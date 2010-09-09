
from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.delta_cmd import *


class Update(DeltaCmd):
    _cmd = 'update'

    def setup(self):
        self.newurl = self.link.url

    def complete(self):
        repos = self.link.repos
        url = self.link.url

        depth = None
        send_copyfrom = False

        print "XX: %s" % self.args

        if len(self.args[0]) == 0:
            rev = repos.get_latest_rev()
        else:
            rev = int(self.args[0][0])
        path = parse.string(self.args[1])

        recurse = self.args[2] == 'true'

        if len(self.args) > 3:
            depth = self.args[3]
            send_copyfrom = parse.bool(self.args[4])

        self.link.send_msg(gen.tuple('target-rev', rev))

        self.send_response(path, url, rev)
