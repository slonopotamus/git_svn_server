from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class CheckPath(SimpleCommand):
    _cmd = 'check-path'

    def do_cmd(self, repo):
        """
        :type repo: GitSvnServer.repository.Repository
        """
        args = self.args
        path = self.link.url
        rev = None

        path = '/'.join(filter(None, [path, parse.string(args.pop(0))]))

        if len(self.args) > 0:
            arg = self.args.pop(0)
            if len(arg) > 0:
                rev = int(arg[0])

        with repo.read_lock:
            f = repo.find_file(path, rev)

        if f is None:
            kind = 'none'
        else:
            kind = f.kind

        self.link.send_msg(gen.success(kind))
