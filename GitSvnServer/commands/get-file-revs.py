
from GitSvnServer import parse, svndiff
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class GetFileRevs (SimpleCommand):
    _cmd = 'get-file-revs'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        start_rev = None
        end_rev = None
        include_merged_revs = False

        path = parse.string(args.pop(0))
        if len(path) > 0:
            url = '/'.join((url, path))

        arg = args.pop(0)
        if len(arg) > 0:
            start_rev = int(arg[0])
            if start_rev == 0:
                start_rev = 1

        arg = args.pop(0)
        if len(arg) > 0:
            end_rev = int(arg[0])
            if end_rev == 0:
                end_rev = 1

        if len(args) > 0:
            include_merged_revs = parse.bool(args[0])
            # TODO: should do something with this ... but what does it mean?

        base_url = repos.get_base_url()

        path = url[len(base_url):]

        diff_version = 0
        if 'svndiff1' in self.link.client_caps:
            diff_version = 1

        prev_rev = None
        for entry in repos.log(url, [''], start_rev, end_rev, end_rev):
            changed, rev, author, date, msg, has_children, revprops = entry

            revprops = [gen.list(gen.string('svn:date'), gen.string(date))]
            revprops.append(gen.list(gen.string('svn:author'),
                                     gen.string(author)))
            revprops.append(gen.list(gen.string('svn:log'), gen.string(msg)))
            response = gen.string(path), rev, gen.list(*revprops), gen.list()
            self.link.send_msg(gen.list(*response))

            r, p, contents = repos.get_file(url, rev)
            if prev_rev is None:
                pcontents = None
            else:
                # Get the previous contents (as independant file contents -
                # hence the True) to produce a diff
                r, p, pcontents = repos.get_file(url, prev_rev, True)
            prev_rev = rev

            encoder = svndiff.Encoder(contents, pcontents, version=diff_version)
            diff_chunk = encoder.get_chunk()
            while diff_chunk is not None:
                self.link.send_msg(gen.string(diff_chunk))
                diff_chunk = encoder.get_chunk()

            self.link.send_msg(gen.string(''))

        self.link.send_msg('done')

        self.link.send_msg(gen.success())
