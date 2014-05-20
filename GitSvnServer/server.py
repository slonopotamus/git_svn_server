#!/usr/bin/python

import re
from SocketServer import *
import signal
import sys
import os
import socket

import auth
import client
import command
import editor
import report
import generate as gen
from errors import *


addr_family = socket.AF_INET
all_interfaces = "0.0.0.0"
if socket.has_ipv6:
    addr_family = socket.AF_INET6
    all_interfaces = "::"

ipv4_re = re.compile(r'\d{1,3}(\.\d{1,3}){3,3}')


def is_ipv4_addr(ip):
    return ipv4_re.match(ip) is not None


def get_address(ip, port):
    if ip is None:
        ip = all_interfaces
    elif socket.has_ipv6 and is_ipv4_addr(ip):
        ip = '::ffff:%s' % ip
    if socket.has_ipv6:
        address = (ip, port, 0, 0)
    else:
        address = (ip, port)
    return address


class SvnServer(ThreadingTCPServer):
    address_family = addr_family
    allow_reuse_address = True

    def __init__(self, options, repo_map):
        self.options = options
        self.log = options.log
        self.repo_map = repo_map
        address = get_address(options.ip, options.port)
        ThreadingTCPServer.__init__(self, address, SvnRequestHandler)

    def start(self):
        if self.options.debug:
            self.log = None

        if self.options.foreground or self.options.debug:
            if self.options.pidfile is not None:
                pf = open(self.options.pidfile, 'w')
                pf.write('%d\n' % os.getpid())
                pf.close()
            return self.run()

        pid = os.fork()
        if pid == 0:
            self.run()
            os._exit(0)

        if self.options.pidfile is not None:
            pf = open(self.options.pidfile, 'w')
            pf.write('%d\n' % pid)
            pf.close()

    def stop(self, *args):
        print 'stopped serving'
        if self.log is not None:
            sys.stdout.flush()
            sys.stdout.close()
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGTERM, self.stop)

        if self.log is not None:
            sys.stdout = open(self.log, 'a')
            sys.stderr = sys.stdout

        print 'start serving'

        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass

        print 'stopped serving'

        if self.log is not None:
            sys.stdout.flush()
            sys.stdout.close()


class SvnRequestHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server):
        """

        :type server: SvnServer
        """
        self.mode = 'connect'
        self.client_caps = None
        self.repos = None
        self.auth = None
        self.data = None
        self.base_url = None
        self.url = None
        self.username = None
        self.command = None
        self.options = server.options
        if server.log is not None:
            sys.stdout = open(server.log, 'a')
            sys.stderr = sys.stdout
        StreamRequestHandler.__init__(self, request, client_address, server)

    def debug(self, msg, send=False):
        if not self.options.show_messages:
            return
        d = '<'
        if send:
            d = '>'
        max_dbg_mlen = self.options.max_message_debug_len
        if max_dbg_mlen > 0 and len(msg) > max_dbg_mlen:
            sys.stderr.write('%d%s%s...\n' % (os.getpid(), d, msg[:max_dbg_mlen]))
        else:
            sys.stderr.write('%d%s%s\n' % (os.getpid(), d, msg))

    def set_mode(self, mode):
        if mode not in ['connect', 'auth', 'announce',
                        'command', 'editor', 'report']:
            raise ModeError("Unknown mode '%s'" % mode)

        self.mode = mode

    def read_msg(self):
        t = self.rfile.read(1)

        while t in [' ', '\n', '\r']:
            t = self.rfile.read(1)

        if len(t) == 0:
            raise EOF()

        if t != '(':
            raise ReadError(t)

        depth = 1

        while depth > 0:
            ch = self.rfile.read(1)

            if ch == '(':
                depth += 1

            if ch == ')':
                depth -= 1

            t += ch

        self.debug(t)
        return t

    def read(self, count):
        data = ''

        while len(data) < count:
            s = self.rfile.read(count - len(data))

            if len(s) == 0:
                raise EOF

            data += s

        self.debug(data)
        return data

    def read_str(self):
        ch = self.rfile.read(1)

        if len(ch) == 0:
            raise EOF

        l = ""
        while ch not in [':', '']:
            l += ch
            ch = self.rfile.read(1)

        bytes = int(l)
        data = ''

        while len(data) < bytes:
            s = self.rfile.read(bytes - len(data))

            if len(s) == 0:
                raise EOF

            data += s

        self.debug(data)
        return data

    def send(self, msg):
        self.debug(msg, send=True)
        self.wfile.write('%s' % msg)
        self.wfile.flush()

    def send_msg(self, msg):
        self.send('%s\n' % msg)

    def send_server_id(self):
        self.send_msg(gen.success(gen.string(self.repos.uuid),
                                  gen.string(self.base_url)))

    def handle(self):
        sys.stderr.write('%d: -- NEW CONNECTION --\n' % os.getpid())
        msg = None
        try:
            while True:
                sys.stdout.flush()
                try:
                    if self.mode == 'connect':
                        self.url, self.client_caps, self.repos, self.base_url = client.connect(self)

                        if self.client_caps is None or self.repos is None:
                            return

                        self.mode = 'auth'

                    elif self.mode == 'auth':
                        if self.username is None:
                            self.username = auth.perform_auth(self)
                            self.mode = 'announce'
                        else:
                            self.send_msg(gen.success(gen.list(), gen.string('')))
                            self.mode = self.data

                        if self.username is None:
                            return

                    elif self.mode == 'announce':
                        self.send_server_id()
                        self.mode = 'command'

                    elif self.mode == 'command':
                        if self.command is None:
                            self.command = command.process(self)
                        else:
                            self.command = self.command.process()

                    elif self.mode == 'editor':
                        editor.process(self)

                    elif self.mode == 'report':
                        report.process(self)

                    else:
                        raise ModeError("unknown mode '%s'" % self.mode)

                except ChangeMode as cm:
                    self.mode = cm.args[0]
                    if len(cm.args) > 1:
                        self.data = cm.args[1]
        except EOF:
            msg = 'EOF'
        except socket.error as e:
            errno, msg = e
        sys.stderr.write('%d: -- CLOSE CONNECTION (%s) --\n' %
                         (os.getpid(), msg))
        sys.stderr.flush()
