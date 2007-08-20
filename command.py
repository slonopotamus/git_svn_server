
import generate as gen
import parse

from cmd_base import *

class LatestRev(SimpleCommand):
    _cmd = 'get-latest-rev'

    def do_cmd(self):
        repos = self.link.repos

        latest_rev = repos.get_latest_rev()

        self.link.send_msg(gen.success(latest_rev))

class CheckPath(SimpleCommand):
    _cmd = 'check-path'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args[0])
        if len(path) > 0:
            url = '/'.join((url_base, path))

        if len(args) > 1:
            rev = int(args[1][0])

        ref, path = repos.parse_url(url)

        print "ref: %s" % ref
        print "path: %s" % path
        print "rev: %s" % rev

        if ref is None or path == '':
            type = 'dir'
        else:
            type = repos.svn_node_kind(url, rev)

        self.link.send_msg(gen.success(type))

class Stat(SimpleCommand):
    _cmd = 'stat'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args[0])
        if len(path) > 0:
            url = '/'.join((url_base, path))

        if len(args) > 1:
            rev = int(args[1][0])

        ref, path = repos.parse_url(url)

        print "ref: %s" % ref
        print "path: %s" % path
        print "rev: %s" % rev

        path, kind, size, changed, by, at = repos.stat(url, rev)

        ls_data = gen.list(kind,
                           size,
                           'false', # has-props
                           changed,
                           gen.list(gen.string(at)),
                           gen.list(gen.string(by)))

        self.link.send_msg(gen.success(gen.list(ls_data)))

class GetDir(SimpleCommand):
    _cmd = 'get-dir'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args.pop(0))
        if len(path) > 0:
            url = '/'.join((url_base, path))

        arg = args.pop(0)
        if isinstance(arg, list):
            rev = int(arg[0])
            arg = args.pop(0)

        want_props = parse.bool(arg)

        want_contents = parse.bool(args.pop(0))

        fields = []
        if len(args) > 0:
            fields = args[0]

        ref, path = repos.parse_url(url)

        print "ref: %s" % ref
        print "path: %s" % path
        print "rev: %s" % rev
        print "want_props: %s" % want_props
        print "want_contents: %s" % want_contents
        print "fields: %s" % fields

        ls_data = []

        for path, kind, size, changed, by, at in repos.ls(url, rev):
            ls_data.append(gen.list(gen.string(path),
                                    kind,
                                    size,
                                    'false', # has-props
                                    changed,
                                    gen.list(gen.string(at)),
                                    gen.list(gen.string(by))))

        response = "%d ( ) %s" % (rev, gen.list(*ls_data))

        self.link.send_msg(gen.success(response))

def process(link):
    msg = parse.msg(link.read_msg())

    command = msg[0]
    args = msg [1]

    if command not in commands:
        link.send_msg(gen.error(210001, "Unknown command '%s'" % command))
        return None

    print "found %s %s" % (command, commands[command](link, args))

    return commands[command](link, args)
