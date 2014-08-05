from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class LatestRev(SimpleCommand):
    _cmd = 'get-latest-rev'

    def do_cmd(self, repo):
        """
        :type repo: GitSvnServer.repository.Repository
        """
        with repo.read_lock:
            latest_rev = repo.get_latest_rev()
        self.link.send_msg(gen.success(latest_rev))
