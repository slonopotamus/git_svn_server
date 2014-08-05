from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class Reparent(SimpleCommand):
    _cmd = 'reparent'

    def do_cmd(self, repo):
        args = self.args

        url = parse.string(args.pop(0))

        if url:
            new_repo, path, base_url = self.link.server.find_repo(url)
            if new_repo != repo:
                self.link.send_msg(gen.error("URL %s is outside of repository %s" % url, self.link.base_url))
                return

            self.link.url = path

        self.link.send_msg(gen.success())
