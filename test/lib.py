
import os
import shutil
import signal
import socket
import sys
import tempfile
import time

from CleverSheep.Test import ProcMan
from CleverSheep.Test.Tester import *


base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
scratch_dir = os.path.join(base_dir, 'scratch')
tar_dir = os.path.join(base_dir, 'test_repo_tars')
git_svnserver = os.path.join(base_dir, '..', 'git-svnserver')
init_db = os.path.join(base_dir, '..', 'git_side_scripts', 'init_db')


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


class TestSuite (Suite):
    ip = '127.0.0.1'
    port = 40000

    def __init__(self):
        self.server = None
        self.scratch = None
        super(TestSuite, self).__init__()

    def start_server(self, config=None):
        if config is None:
            config = 'empty'
        cfg_file = os.path.join(self.scratch, '%s.cfg' % config)
        fd, self.pidfile = tempfile.mkstemp(suffix='.pid')
        cwd = os.getcwd()
        os.chdir(self.scratch)
        self.server = start_server(cfg_file, self.pidfile, self.ip, self.port)
        os.chdir(cwd)
        time.sleep(0.2)

    def stop_server(self):
        if self.server is None:
            return

        stop_server(self.pidfile, self.server)
        self.pidfile = None
        self.sever = None

    def server_pid(self):
        return get_pid(self.pidfile)

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
