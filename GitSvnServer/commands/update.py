from GitSvnServer.delta_cmd import *


class Update(DeltaCmd):
    _cmd = 'update'

    def setup(self):
        self.newurl = self.link.url

    def complete(self):
        depth = None
        send_copyfrom = False

        arg = self.args.pop(0)
        if len(arg) > 0:
            rev = int(arg[0])
        else:
            rev = None

        path = parse.string(self.args.pop(0))

        recurse = parse.bool(self.args.pop(0))

        if self.args:
            depth = self.args.pop(0)
            send_copyfrom = parse.bool(self.args.pop(0))

        self.send_response(path, self.link.url, rev)
