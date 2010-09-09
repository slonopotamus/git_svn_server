
from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.delta_cmd import *


class Diff(DeltaCmd):
    _cmd = 'diff'

    def setup(self):
        self.newurl = parse.string(self.args[4])

    def complete(self):
        repos = self.link.repos

        text_deltas = True
        depth = None

        print "XX: %s" % self.args

        if len(self.args[0]) == 0:
            rev = repos.get_latest_rev()
        else:
            rev = int(self.args[0][0])
        path = parse.string(self.args[1])

        recurse = parse.bool(self.args[2])

        ignore_ancestry = parse.bool(self.args[3])

        url = parse.string(self.args[4])

        if len(self.args) > 5:
            ignore_ancestry = parse.bool(self.args[5])

        if len(self.args) > 6:
            depth = self.args[6]

        self.link.send_msg(gen.tuple('target-rev', rev))

        self.send_response(path, url, rev)
