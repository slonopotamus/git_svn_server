
import generate as gen
import md5
import parse

from cmd_base import *

class Reparent (SimpleCommand):
    _cmd = 'reparent'

    def do_cmd(self):
        args = self.args

        url = parse.string(args.pop(0))

        if len(url) > 0:
            print "new url: %s" % url
            self.link.url = url

        self.link.send_msg(gen.success())


