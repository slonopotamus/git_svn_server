from GitSvnServer import parse
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class Log(SimpleCommand):
    _cmd = 'log'

    def do_cmd(self, repo):
        """
        :type repo: GitSvnServer.repository.Repository
        """
        args = self.args
        url = self.link.url
        start_rev = None
        end_rev = None

        target_paths = [parse.string(x) for x in args.pop(0)]

        arg = args.pop(0)
        if len(arg) > 0:
            start_rev = int(arg[0])
            if start_rev == 0:
                start_rev = 1

        arg = args.pop(0)
        if args:
            end_rev = int(arg[0])
            if end_rev == 0:
                end_rev = 1

        send_changed_paths = parse.bool(args.pop(0))

        strict_node = parse.bool(args.pop(0))

        limit = 0
        if args:
            limit = int(args.pop(0))

        include_merged_revisions = False
        if args:
            include_merged_revisions = parse.bool(args.pop(0))

        # all-revprops | revprops

        # ( revprop:string ... )

        # TODO(marat): we perform I/O while holding read lock. This is bad for concurrency.
        with repo.read_lock:
            for entry in repo.log(url, target_paths, start_rev, end_rev, limit):
                changed_paths = []

                if send_changed_paths:
                    for path, mode in entry.changed_paths.items():
                        # TODO(marat): props
                        # Property modification
                        pmod = False

                        # TODO(marat): what's this?
                        tmod = True

                        # TODO(marat): copy/move detection
                        # copy = gen.list(gen.string(cp), cr)
                        copy = gen.list()

                        ct = gen.list(gen.string('file'), gen.bool(tmod), gen.bool(pmod))
                        changed_paths.append(gen.list(gen.string(path), mode, copy, ct))

                log_entry = gen.list(gen.list(*changed_paths),
                                     entry.rev.number,
                                     entry.rev.gen_author(),
                                     entry.rev.gen_date(),
                                     gen.list(gen.string(entry.rev.message())))
                self.link.send_msg(log_entry)

        self.link.send_msg('done')
        self.link.send_msg(gen.success())
