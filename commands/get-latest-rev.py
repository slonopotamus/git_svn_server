
import generate as gen
import md5
import parse

from cmd_base import *

class LatestRev(SimpleCommand):
    _cmd = 'get-latest-rev'

    def do_cmd(self):
        repos = self.link.repos

        latest_rev = repos.get_latest_rev()

        self.link.send_msg(gen.success(latest_rev))

