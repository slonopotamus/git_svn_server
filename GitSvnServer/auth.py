import hmac
from email.utils import make_msgid

import generate as gen
import parse


class AuthFailure(Exception):
    pass


class AuthMethod:
    def __init__(self, link, auth_db):
        """

        :type link: SvnRequestHandler
        """
        self.link = link
        self.auth_db = auth_db

    def get_response(self):
        return self.link.read_str()

    def perform_auth(self):
        raise NotImplemented()

    def do_auth(self):
        while True:
            try:
                return self.perform_auth()
            except AuthFailure, fail:
                self.link.send_msg(gen.failure(*fail.args))
                return False


class CramMd5Auth(AuthMethod):
    def perform_auth(self):
        msg_id = make_msgid()
        self.link.send_msg(gen.tuple('step', gen.string(msg_id)))

        resp = self.get_response()
        username, pass_hash = resp.rsplit(' ', 1)

        with self.link.repos.lock:
            password = str(self.auth_db.get_password(username))

        if password is None:
            raise AuthFailure(gen.string('unknown user'))

        if pass_hash != hmac.new(password, msg_id).hexdigest():
            raise AuthFailure(gen.string('incorrect password'))

        self.link.send_msg(gen.success())
        return username


auths = {
    'CRAM-MD5': CramMd5Auth,
}


def perform_auth(link):
    """

    :type link: SvnRequestHandler
    """
    auth_db = link.repos.get_auth()

    link.send_msg(gen.success(gen.list(*auths.keys()), gen.string(link.repos.base_url)))

    while True:
        auth_type = parse.msg(link.read_msg())[0]

        if auth_type not in auths:
            link.send_msg(gen.failure(gen.string('unknown auth type: %s' % auth_type)))
            continue

        auth = auths[auth_type](link, auth_db)

        username = auth.do_auth()
        if username:
            return username
