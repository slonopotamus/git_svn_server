from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class LatestRev(SimpleCommand):
    _cmd = 'get-latest-rev'

    @need_repo_lock
    def do_cmd(self):
        repos = self.link.repos

        latest_rev = repos.get_latest_rev()

        if latest_rev is None:
            msg = gen.error(210005, "No respository found in '%s'" % self.link.url)
        else:
            msg = gen.success(latest_rev)

        self.link.send_msg(msg)
