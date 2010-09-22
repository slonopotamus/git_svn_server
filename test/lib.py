
import os
import shutil
import signal
import socket
import sqlite3
import sys
import tempfile
import time
import xml.etree.cElementTree as ElementTree

from CleverSheep.Test import ProcMan
from CleverSheep.Test.Tester import *


base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
scratch_dir = os.path.join(base_dir, 'scratch')
tar_dir = os.path.join(base_dir, 'test_repo_tars')
git_svnserver = os.path.join(base_dir, '..', 'git-svnserver')
init_db = os.path.join(base_dir, '..', 'git_side_scripts', 'init_db')


svn_binary = 'svn'


def start_server(config, pidfile, ip, port):
    cmd = '%s -c %s -d -i %s -p %d --pidfile %s' % \
          (git_svnserver, config, ip, port, pidfile)
    return ProcMan.run_in_xterm('git-svnserver', cmd)


def get_pid(pidfile):
    try:
        pf = open(pidfile)
        pid = pf.read().strip()
        pf.close()
        return int(pid)
    except:
        return None


def stop_server(pidfile, server):
    pid = get_pid(pidfile)
    os.remove(pidfile)
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
    a = time.time()
    while server and time.time() - a < 10:
        if server.poll() is not None:
            break
        time.sleep(0.1)
    else:
        os.kill(pid, signal.SIGKILL)


def create_new_scratch():
    if not os.path.exists(scratch_dir):
        os.makedirs(scratch_dir)
    scratch = tempfile.mkdtemp(dir=scratch_dir)
    return scratch


def clean_scratch(scratch):
    shutil.rmtree(scratch)


try:
    from subprocess import Popen, PIPE
    def run_cmd(cmd):
        p = Popen(cmd, shell=True,
                  stdin=PIPE, stdout=PIPE, stderr=PIPE,
                  close_fds=True)
        return p.stdin, p.stdout, p.stderr
except ImportError:
    def run_cmd(cmd):
        return os.popen3(self._cmd)


class SvnData (object):
    def __init__(self, username, password, command_string):
        self._cmd = "%s --no-auth-cache --non-interactive --username '%s' " \
                    "--password '%s' %s" % \
                    (svn_binary, username, password, command_string)
        print 'cmd', self._cmd
        self.open()

    def open(self):
        self._in, self._data, self._err = run_cmd(self._cmd)

    def read(self, l=-1):
        return self._data.read(l)

    def close(self):
        self._in.close()
        self._data.close()
        self._err.close()

    def reopen(self):
        self.close()
        self.open()


class TestSuite (Suite):
    ip = '127.0.0.1'
    port = 40000
    username = 'test'
    password = ''

    def __init__(self):
        self.server = None
        self.scratch = None
        super(TestSuite, self).__init__()

    def get_svn_url(self, repos=None, path=None):
        if repos is None:
            repos = 'empty'
        url = "svn://%s:%d/%s" % (self.ip, self.port, repos)
        if path is not None:
            url = "%s/%s" % (url, path)
        return url

    def get_svn_data(self, command_string, username=None, password=None):
        if username is None:
            username = self.username
        if password is None:
            password = self.password
        svn_data = SvnData(username, password, command_string)

        data = [line.strip('\n') for line in svn_data._data]

        svn_data.close()

        return data

    def get_svn_xml(self, command_string, username=None, password=None):
        if username is None:
            username = self.username
        if password is None:
            password = self.password
        svn_data = SvnData(username, password, "--xml %s" % command_string)

        element = ElementTree.parse(svn_data._data)

        svn_data.close()

        return element.getroot()

    def start_server(self, config=None):
        if config is None:
            config = 'empty'
        cfg_file = os.path.join(self.scratch, '%s.cfg' % config)
        fd, self.pidfile = tempfile.mkstemp(suffix='.pid')
        cwd = os.getcwd()
        os.chdir(self.scratch)
        self.server = start_server(cfg_file, self.pidfile, self.ip, self.port)
        os.chdir(cwd)
        time.sleep(0.5)

    def stop_server(self):
        if self.server is None:
            return

        stop_server(self.pidfile, self.server)
        self.pidfile = None
        self.sever = None

    def server_pid(self):
        return get_pid(self.pidfile)

    def db_sql(self, repos, sql, *args):
        git_dir = os.path.join(self.scratch, repos)
        db_path = os.path.join(git_dir, 'svnserver/db')
        conn = sqlite3.connect(db_path, isolation_level='IMMEDIATE')
        rows = conn.execute(sql, args).fetchall()
        conn.commit()
        conn.close()

        return rows

    def add_user(self, repos=None, username=None, password=None,
                 name=None, email=None):
        if repos is None:
            repos = 'empty'
        if username is None:
            username = self.username
        if password is None:
            password = self.password
        if name is None:
            name = username
        if email is None:
            email = '%s@example.com' % name
        self.db_sql(repos, 'INSERT INTO users VALUES (?,?,?,?)',
                    username, name, email, password)

    def delete_user(self, repos=None, username=None):
        if repos is None:
            repos = 'empty'
        if username is None:
            username = self.username
        self.db_sql(repos, 'DELETE FROM users WHERE username=?', username)

    def create_empty_repos(self, name):
        cwd = os.getcwd()
        git_dir = os.path.join(self.scratch, name)
        os.mkdir(git_dir)
        os.chdir(git_dir)
        os.system('git init --bare -q')
        os.system(init_db)
        os.chdir(cwd)
        cfg = open(os.path.join(self.scratch, '%s.cfg' % name), 'w')
        cfg.write('[repos "%s"]\n' % name)
        cfg.write('    location = %s\n' % git_dir)
        cfg.close()
        npr = os.path.join(base_dir, '..', 'git_side_scripts',
                           'noddy-post-receive')
        shutil.copy(npr, os.path.join(git_dir, 'hooks', 'post-receive'))
        self.add_user()

    def create_repos_from_tar(self, name, tarname):
        cwd = os.getcwd()
        git_dir = os.path.join(self.scratch, name)
        tarpath = os.path.join(tardir, tarname)
        os.mkdir(git_dir)
        os.chdir(git_dir)
        os.system('tar xvf %s' % tarfile)
        os.chdir(cwd)
        cfg = open(os.path.join(self.scratch, '%s.cfg' % name), 'w')
        cfg.write('[repos "%s"]\n' % name)
        cfg.write('    location = %s\n' % git_dir)
        cfg.close()

    def setUp(self):
        self.scratch = create_new_scratch()
        self.create_empty_repos('empty')

    def tearDown(self):
        if self.scratch is not None:
            clean_scratch(self.scratch)
            self.scratch = None

        self.stop_server()

        for attrib in ['ip', 'port']:
            if attrib in self.__dict__:
                del self.__dict__[attrib]

    def connect_to_server(self, ip=None, port=None):
        if ip is None:
            ip = self.ip
        if port is None:
            port = self.port

        s = socket.socket()
        error = s.connect_ex((ip, port))
        return s, error
