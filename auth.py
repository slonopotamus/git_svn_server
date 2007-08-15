
from email.Utils import make_msgid
import hmac

import generate as gen
import parse

class Needed(Exception):
    pass

class AuthFailure(Exception):
    pass

class AuthMethod:
    def __init__(self, inf, outf):
        self.rfile = inf
        self.wfile = outf

    def get_response(self):
        ch = self.rfile.read(1)

        if len(ch) == 0:
            raise EOF

        l = ""
        while ch not in [':', '']:
            l += ch
            ch = self.rfile.read(1)

        bytes = int(l)
        print "want %d bytes" % bytes
        data = self.rfile.read(bytes)

        return data

    def do_auth(self, next):
        while True:
            try:
                self.perform_auth()
                break
            except AuthFailure, fail:
                self.wfile.write('%s\n' % gen.failure(*fail.args))

        self.wfile.write('%s\n' % gen.success())

        return next()

class CramMd5Auth(AuthMethod):
    def perform_auth(self):
        msg_id = make_msgid()
        self.wfile.write('%s\n' % gen.tuple('step', gen.string(msg_id)))

        resp = self.get_response()
        print resp
        username, pass_hash = resp.split()

        if pass_hash != hmac.new('test', msg_id).hexdigest():
            raise AuthFailure(gen.string('incorrect password'))

auths = {
    'CRAM-MD5' : CramMd5Auth,
}
