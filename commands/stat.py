
import generate as gen
import md5
import parse

from cmd_base import *

class Stat(SimpleCommand):
    _cmd = 'stat'

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

##        ref, path = repos.parse_url(url)

##        print "ref: %s" % ref
##        print "path: %s" % path
##        print "rev: %s" % rev

        path, kind, size, changed, by, at = repos.stat(url, rev)

        if path is None:
            self.link.send_msg(gen.success(gen.list()))

        else:
            ls_data = gen.list(kind,
                               size,
                               'false', # has-props
                               changed,
                               gen.list(gen.string(at)),
                               gen.list(gen.string(by)))

            self.link.send_msg(gen.success(gen.list(ls_data)))


