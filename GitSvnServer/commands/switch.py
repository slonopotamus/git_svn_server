
from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.delta_cmd import *


class Switch(DeltaCmd):
    _cmd = 'switch'

    def setup(self):
        self.newurl = parse.string(self.args[3])

    def complete(self):
        repos = self.link.repos

        depth = None

        print "XX: %s" % self.args

        if len(self.args[0]) == 0:
            rev = repos.get_latest_rev()
        else:
            rev = int(self.args[0][0])
        path = parse.string(self.args[1])

        recurse = parse.bool(self.args[2])

        url = parse.string(self.args[3])

        if len(self.args) > 4:
            depth = self.args[4]

        self.link.send_msg(gen.tuple('target-rev', rev))

        self.send_response(path, url, rev)
