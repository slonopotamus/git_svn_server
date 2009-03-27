
import os
import signal
import tempfile
import time

from CleverSheep.Test import ProcMan
from CleverSheep.Test.Tester import *


def start_server(config, pidfile, ip, port):
    cmd = '../git-svnserver -c %s -d -i %s -p %d --pidfile %s' % \
          (config, ip, port, pidfile)
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
    pass


def clean_scratch(scratch):
    pass


class TestSuite (Suite):
    ip = '127.0.0.1'
    port = 40000

    def __init__(self):
        self.server = None
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
        clean_scratch(self.scratch)
        self.stop_server()
