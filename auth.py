
from email.Utils import make_msgid
import hmac

import generate as gen
import parse

class Needed(Exception):
    pass

class AuthFailure(Exception):
    pass

class AuthMethod:
    def __init__(self, link):
        self.link = link

    def get_response(self):
        return self.link.read_str()

    def do_auth(self):
        while True:
            try:
                self.perform_auth()
                break
            except AuthFailure, fail:
                self.link.send_msg(gen.failure(*fail.args))
                return False

        self.link.send_msg(gen.success())

        return True

    def reauth(self):
        self.link.send_msg(success('( )', string('')))

class CramMd5Auth(AuthMethod):
    def perform_auth(self):
        msg_id = make_msgid()
        self.link.send_msg(gen.tuple('step', gen.string(msg_id)))

        resp = self.get_response()
        print resp
        username, pass_hash = resp.split()

        if pass_hash != hmac.new('test', msg_id).hexdigest():
            raise AuthFailure(gen.string('incorrect password'))

auths = {
    'CRAM-MD5' : CramMd5Auth,
}

def auth(link):
    auth_list = auths.keys()
    link.send_msg(gen.success(gen.list(*auth_list), gen.string('test')))

    msg = link.read_msg()

    auth_type = parse.msg(msg)[0]

    if auth_type not in auths:
        link.send_msg(gen.failure(gen.string('unknown auth type: %s' \
                                             % auth_type)))
        return None

    auth = auths[auth_type](link)

    if not auth.do_auth():
        return None

    return auth
