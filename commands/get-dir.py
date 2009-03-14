
import generate as gen
import md5
import parse

from cmd_base import *

class GetDir(SimpleCommand):
    _cmd = 'get-dir'

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
            fields = args[0]

        ls_data = []
        if want_contents:
            for path, kind, size, changed, by, at in repos.ls(url, rev):
                path_url = "%s/%s" % (url, path)
                if len(repos.get_props(path_url, rev, False)) == 0:
                    has_props = 'false'
                else:
                    has_props = 'true'
                print path_url, has_props
                ls_data.append(gen.list(gen.string(path),
                                        kind,
                                        size,
                                        has_props,
                                        changed,
                                        gen.list(gen.string(at)),
                                        gen.list(gen.string(by))))

        p = []
        if want_props:
            for name, value in repos.get_props(url, rev):
                p.append(gen.list(gen.string(name), gen.string(value)))

        response = "%d %s %s" % (rev, gen.list(*p), gen.list(*ls_data))

        self.link.send_msg(gen.success(response))


