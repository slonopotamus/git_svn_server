from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class Stat(SimpleCommand):
    _cmd = 'stat'

    def do_cmd(self, repo):
        """
        :type repo: GitSvnServer.repository.Repository
        """
        args = self.args
        path = self.link.url
        rev = None

        path = '/'.join(filter(None, [path, parse.string(args.pop(0))]))

        if len(args) > 0:
            rev = int(args.pop(0)[0])
        else:
            rev = None

        with repo.read_lock:
            stat = repo.find_file(path, rev)

        if stat is None:
            self.link.send_msg(gen.success(gen.list()))
            return

        props = list(stat.props(False))

        ls_data = gen.list(stat.kind,
                           stat.size,
                           gen.bool(len(props) > 0),
                           stat.last_change.number,
                           stat.last_change.gen_date(),
                           stat.last_change.gen_author())

        self.link.send_msg(gen.success(gen.list(ls_data)))
