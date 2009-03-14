
import generate as gen
import md5
import parse

from cmd_base import *

class CheckPath(SimpleCommand):
    _cmd = 'check-path'

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

        type = repos.check_path(url, rev)

        self.link.send_msg(gen.success(type))
