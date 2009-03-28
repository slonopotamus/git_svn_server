
import os
import signal
import socket
import sys
import tempfile
import time

from CleverSheep.Test import ProcMan
from CleverSheep.Test.Tester import *


base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
scratch_dir = os.path.join(base_dir, 'scratch')
git_svnserver = os.path.join(base_dir, '..', 'git-svnserver')


def start_server(config, pidfile, ip, port):
    cmd = '%s -c %s -d -i %s -p %d --pidfile %s' % \
          (git_svnserver, config, ip, port, pidfile)
    print cmd
    return ProcMan.run_in_xterm('git-svnserver', cmd)


def get_pid(pidfile):
    pf = open(pidfile)
    pid = pf.read().strip()
    pf.close()
    return int(pid)


def stop_server(pidfile, server):
    pid = get_pid(pidfile)
    os.remove(pidfile)
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
    pass


class TestSuite (Suite):
    ip = '127.0.0.1'
    port = 40000

    def __init__(self):
        self.server = None
        self.scratch = None
        super(TestSuite, self).__init__()

    def start_server(self, config):
        fd, self.pidfile = tempfile.mkstemp(suffix='.pid')
        self.server = start_server(config, self.pidfile, self.ip, self.port)
        time.sleep(0.2)

    def stop_server(self):
        if self.server is None:
            return

        stop_server(self.pidfile, self.server)
        self.pidfile = None
        self.sever = None

    def server_pid(self):
        return get_pid(self.pidfile)

    def setUp(self):
        self.scratch = create_new_scratch()

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
