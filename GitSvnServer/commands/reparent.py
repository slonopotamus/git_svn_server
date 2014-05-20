from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.client import find_repo
from GitSvnServer.cmd_base import *


class Reparent(SimpleCommand):
    _cmd = 'reparent'

    def do_cmd(self):
        args = self.args

        url = parse.string(args.pop(0))

        if len(url) > 0:
            new_repo, path, base_url = find_repo(self.link, url)
            if new_repo != self.link.repos:
                self.link.send_msg(gen.error("URL %s is outside of repository %s" % url, self.link.base_url))
                return

            print "new url: %s" % url
            self.link.url = path

        self.link.send_msg(gen.success())
