
from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *

class RevPropList (SimpleCommand):
    _cmd = 'rev-proplist'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args

        rev = int(args.pop(0))

        print 'rev = %d' % rev

        props = []
        for name, value in repos.rev_proplist(rev):
            p = gen.list(gen.string(name), gen.string(value))
            props.append(p)

        response = gen.list(*props)

        self.link.send_msg(gen.success(response))


