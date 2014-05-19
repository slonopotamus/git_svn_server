
from email.Utils import make_msgid
import hmac

import generate as gen
import parse

class DummyAuthDb (object):
    def __init__(self, repos):
        self.repos = repos

    def get_password(self, username):
        return ''

class Needed(Exception):
    pass

class AuthFailure(Exception):
    pass

class AuthMethod:
    def __init__(self, link, auth_db):
        self.link = link
        self.auth_db = auth_db
        self.username = None

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
        self.link.send_msg(gen.success(gen.list(), gen.string('')))

class CramMd5Auth(AuthMethod):
    def perform_auth(self):
        msg_id = make_msgid()
        self.link.send_msg(gen.tuple('step', gen.string(msg_id)))

        resp = self.get_response()
        username, pass_hash = resp.rsplit(' ', 1)

        password = str(self.auth_db.get_password(username))
        if password is None:
            raise AuthFailure(gen.string('unknown user'))

        if pass_hash != hmac.new(password, msg_id).hexdigest():
            raise AuthFailure(gen.string('incorrect password'))

        print "Authenticated:", username
        self.username = username

auths = {
    'CRAM-MD5' : CramMd5Auth,
}

def auth(link):
    auth_db = link.repos.get_auth()

    link.send_msg(gen.success(gen.list(*auths.keys()), gen.string(link.repos.base_url)))

    while True:
        auth_type = parse.msg(link.read_msg())[0]

        if auth_type not in auths:
            link.send_msg(gen.failure(gen.string('unknown auth type: %s' \
                                                 % auth_type)))
            continue

        auth = auths[auth_type](link, auth_db)

        if auth.do_auth():
            return auth
