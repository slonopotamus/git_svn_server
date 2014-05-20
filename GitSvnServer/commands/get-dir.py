from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class GetDir(SimpleCommand):
    _cmd = 'get-dir'

    @need_repo_lock
    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args.pop(0))
        if len(path) > 0:
            url = '/'.join((url, path))

        arg = args.pop(0)
        if len(arg) > 0:
            rev = int(arg[0])

        want_props = parse.bool(args.pop(0))

        want_contents = parse.bool(args.pop(0))

        fields = []
        if len(args) > 0:
            fields = args.pop(0)

        ls_data = []
        if want_contents:
            for path, kind, size, changed, by, at in repos.ls(url, rev):
                path_url = "%s/%s" % (url, path)
                has_props = len(repos.get_props(path_url, rev, False)) == 0
                if by is None:
                    by = gen.list()
                else:
                    by = gen.list(gen.string(by))

                ls_data.append(gen.list(gen.string(path),
                                        kind,
                                        size,
                                        gen.bool(has_props),
                                        changed,
                                        gen.list(gen.string(at)),
                                        by))

        p = []
        if want_props:
            for name, value in repos.get_props(url, rev):
                p.append(gen.list(gen.string(name), gen.string(value)))

        response = "%d %s %s" % (rev, gen.list(*p), gen.list(*ls_data))

        self.link.send_msg(gen.success(response))
