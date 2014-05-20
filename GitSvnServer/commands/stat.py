from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class Stat(SimpleCommand):
    _cmd = 'stat'

    @need_repo_lock
    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args[0])
        if len(path) > 0:
            url = '/'.join((url, path))

        if len(args) > 1:
            rev = int(args[1][0])

        path, kind, size, changed, by, at = repos.stat(url, rev)

        if path is None:
            self.link.send_msg(gen.success(gen.list()))
            return

        props = repos.get_props(url, rev, False)

        if by is None:
            by = gen.list()
        else:
            by = gen.list(gen.string(by))

        ls_data = gen.list(kind,
                           size,
                           gen.bool(len(props) > 0),
                           changed,
                           gen.list(gen.string(at)),
                           by)

        self.link.send_msg(gen.success(gen.list(ls_data)))
