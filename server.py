#!/usr/bin/python

import os
from SocketServer import *
import sys

import auth
from config import config
import message as msg

class EOF(Exception):
    pass

class ReadError(Exception):
    pass

class SvnServer(ForkingTCPServer):
    allow_reuse_address = True
    pass

class SvnRequestHandler(StreamRequestHandler):
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

    def handle(self):
        sys.stderr.write('%d: -- NEW CONNECTION --\n' % os.getpid())
        try:
            resp = msg.greeting()
            while resp != None:
                sys.stderr.write('%d>%s\n' % (os.getpid(), resp))
                self.wfile.write('%s\n' % resp)
                try:
                    resp = msg.handle_msg(self.read_msg())
                except auth.Needed, nauth:
                    auth_type = nauth.args[0]
                    next_resp_fn = nauth.args[1]
                    auth_engine = auth.auths[auth_type](self.rfile, self.wfile)
                    resp = auth_engine.do_auth(next_resp_fn)
        except EOF:
            pass
        sys.stderr.write('%d: -- CLOSE CONNECTION --\n' % os.getpid())

def main():
    config.load('test.cfg')

    server = SvnServer(('0.0.0.0', 3690), SvnRequestHandler)

    server.serve_forever()

if __name__ == "__main__":
    main()
