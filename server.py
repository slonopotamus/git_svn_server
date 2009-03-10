#!/usr/bin/python

import os
from SocketServer import *
import sys

import auth
import client
import command
import editor
import report
import socket

import generate as gen
from config import config
from errors import *

addr_family = socket.AF_INET
all_interfaces = "0.0.0.0"
if socket.has_ipv6:
    addr_family = socket.AF_INET6
    all_interfaces = "::"

class SvnServer(ForkingTCPServer):
    address_family = addr_family
    allow_reuse_address = True
    pass

class SvnRequestHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server):
        self.mode = 'connect'
        self.client_caps = None
        self.repos = None
        self.auth = None
        self.data = None
        self.url = None
        self.command = None
        StreamRequestHandler.__init__(self, request, client_address, server)

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

        sys.stderr.write('%d<%s\n' % (os.getpid(), t))
        return t

    def read(self, count):
        data = ''

        while len(data) < count:
            s = self.rfile.read(count - len(data))

            if len(s) == 0:
                raise EOF

            data += s

        sys.stderr.write('%d<%s\n' % (os.getpid(), data))
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

        sys.stderr.write('%d<%s\n' % (os.getpid(), data))
        return data

    def send(self, msg):
        if len(msg) > 100:
            sys.stderr.write('%d>%s...\n' % (os.getpid(), msg[:100]))
        else:
            sys.stderr.write('%d>%s\n' % (os.getpid(), msg))
        self.wfile.write('%s' % msg)
        self.wfile.flush()

    def send_msg(self, msg):
        self.send('%s\n' % msg)

    def send_server_id(self):
        self.send_msg(gen.success(gen.string(self.repos.get_uuid()),
                                  gen.string(self.repos.get_base_url())))

    def handle(self):
        sys.stderr.write('%d: -- NEW CONNECTION --\n' % os.getpid())
        try:
            while True:
                try:
                    if self.mode == 'connect':
                        self.url, self.client_caps, self.repos = \
                                  client.connect(self)

                        if self.client_caps is None or self.repos is None:
                            return

                        self.mode = 'auth'

                    elif self.mode == 'auth':
                        if self.auth is None:
                            self.auth = auth.auth(self)
                            self.mode = 'announce'
                        else:
                            self.auth.reauth()
                            self.mode = self.data

                        if self.auth is None:
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

                except ChangeMode, cm:
                    self.mode = cm.args[0]
                    if len(cm.args) > 1:
                        self.data = cm.args[1]
        except EOF:
            pass
        sys.stderr.write('%d: -- CLOSE CONNECTION --\n' % os.getpid())

def main():
    config.load('test.cfg')

    server = SvnServer((all_interfaces, 3690), SvnRequestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
