from GitSvnServer.delta_cmd import *


class Diff(DeltaCmd):
    _cmd = 'diff'

    def setup(self):
        self.newurl = parse.string(self.args[4])

    def complete(self):
        text_deltas = True
        depth = None

        print "XX: %s" % self.args

        arg = self.args.pop(0)
        if len(arg) > 0:
            rev = int(arg[0])
        else:
            rev = None

        path = parse.string(self.args.pop(0))

        recurse = parse.bool(self.args.pop(0))

        ignore_ancestry = parse.bool(self.args.pop(0))

        url = parse.string(self.args.pop(0))

        if len(self.args) > 0:
            ignore_ancestry = parse.bool(self.args.pop(0))

        if len(self.args) > 0:
            depth = self.args.pop(0)

        self.send_response(path, url, rev)
