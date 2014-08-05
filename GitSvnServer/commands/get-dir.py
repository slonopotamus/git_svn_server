from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class GetDir(SimpleCommand):
    _cmd = 'get-dir'

    def do_cmd(self, repo):
        """
        :type repo: GitSvnServer.repository.Repository
        """
        path = self.link.url

        path = '/'.join(filter(None, [path, parse.string(self.args.pop(0))]))

        arg = self.args.pop(0)
        if len(arg) > 0:
            rev = int(arg[0])
        else:
            rev = None

        want_props = parse.bool(self.args.pop(0))
        want_contents = parse.bool(self.args.pop(0))

        fields = []
        if self.args:
            fields = self.args.pop(0)

        props = {}
        ls = []
        with repo.read_lock:
            if want_contents:
                ls = list(repo.ls(path, rev))
            if want_props:
                props = repo.get_props(path, rev)

        p = [gen.list(gen.string(name), gen.string(value)) for name, value in props]

        ls_data = [gen.list(gen.string(name),
                            stat.kind,
                            stat.size,
                            gen.bool(len(list(stat.props(False))) > 0),
                            stat.last_change.number,
                            stat.last_change.gen_date(),
                            stat.last_change.gen_author()) for name, stat in ls]

        response = "%d %s %s" % (rev, gen.list(*p), gen.list(*ls_data))
        self.link.send_msg(gen.success(response))
