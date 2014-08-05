try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class GetFile(SimpleCommand):
    _cmd = 'get-file'

    def do_cmd(self, repo):
        """
        :type repo: GitSvnServer.repository.Repository
        """
        args = self.args
        path = self.link.url
        rev = None

        path = '/'.join(filter(None, [path, parse.string(args.pop(0))]))

        arg = args.pop(0)
        if len(arg) > 0:
            rev = int(arg[0])

        want_props = parse.bool(args.pop(0))
        want_contents = parse.bool(args.pop(0))

        with repo.read_lock:
            f = repo.find_file(path, rev)
            p = []

            if want_props:
                for name, value in f.props():
                    p.append(gen.list(gen.string(name), gen.string(value)))

        blob = repo.pygit[f.blob_id]
        m = md5()
        m.update(blob.data)
        csum = gen.string(m.hexdigest())

        self.link.send_msg(gen.success(*(gen.list(csum), rev, gen.list(*p))))

        if want_contents:
            self.link.send_msg(gen.string(blob.data))
            self.link.send_msg(gen.string(''))
            self.link.send_msg(gen.success())
