
import generate as gen
import md5
import parse

from cmd_base import *

class Update(Command):
    _cmd = 'update'

    def report_set_path(self, path, rev, start_empty, lock_token, depth):
        self.prev_revs[path] = (rev, start_empty)
        print "report: set path"

    def report_link_path(self, path, url, rev, start_empty, lock_token, depth):
        print "report: link path"

    def report_delete_path(self, path):
        print "report: delete path"

    @cmd_step
    def auth(self):
        raise ChangeMode('auth', 'command')

    @cmd_step
    def get_reports(self):
        self.prev_revs = {}
        raise ChangeMode('report')

    @cmd_step
    def send_update(self):
        repos = self.link.repos
        print "XX: %s" % self.args
        rev = int(self.args[0][0])
        path = parse.string(self.args[1])
        recurse = self.args[2] == 'true'
        url = '/'.join((self.link.url, path))

        self.link.send_msg(gen.tuple('target-rev', rev))

        cdir = path
        ctok = 'd0'
        dirs = []

        # TODO: this is not complicated enough - we need to be able to handle
        # the case where the client tells us that different bits of the
        # repository are at different revisions.  Heck, we need to handle the
        # case where there was a previous checkout!

        self.link.send_msg(gen.tuple('open-root', gen.list(rev),
                                     gen.string(ctok)))

        for entry in repos.get_update(url, rev):
            name, kind, tok, props, diff, csum = entry

            path_bits = name.split('/')
            dir = '/'.join(path_bits[:-1])

            while len(dir) < len(cdir) and dir != cdir:
                self.link.send_msg(gen.tuple('close-dir', gen.string(ctok)))
                print "%s vs. %s" % (dir, cdir)
                cdir, ctok = dirs.pop(0)

            if kind == 'dir':
                self.link.send_msg(gen.tuple('add-dir', gen.string(name),
                                             gen.string(ctok), gen.string(tok),
                                             gen.list()))
                for key, value in props.items():
                    if value is None:
                        val = gen.list()
                    else:
                        val = gen.list(gen.string(value))
                    self.link.send_msg(gen.tuple('change-dir-prop',
                                                 gen.string(tok),
                                                 gen.string(key),
                                                 val))
                dirs.insert(0, (cdir, ctok))
                cdir = dir
                ctok = tok

            else:
                self.link.send_msg(gen.tuple('add-file', gen.string(name),
                                             gen.string(ctok), gen.string(tok),
                                             gen.list()))
                for key, value in props.items():
                    if value is None:
                        val = gen.list()
                    else:
                        val = gen.list(gen.string(value))
                    self.link.send_msg(gen.tuple('change-file-prop',
                                                 gen.string(tok),
                                                 gen.string(key),
                                                 val))
                self.link.send_msg(gen.tuple('apply-textdelta', gen.string(tok),
                                             gen.list()))
                for diff_chunk in diff:
                    self.link.send_msg(gen.tuple('textdelta-chunk',
                                                 gen.string(tok),
                                                 gen.string(diff_chunk)))
                self.link.send_msg(gen.tuple('textdelta-end', gen.string(tok)))
                if csum == '':
                    cksum = gen.list()
                else:
                    cksum = gen.list(gen.string(csum))
                self.link.send_msg(gen.tuple('close-file', gen.string(tok),
                                             cksum))

        self.link.send_msg(gen.tuple('close-dir', gen.string(ctok)))

        print "ought to be doing the edit bits here ..."
        self.link.send_msg(gen.tuple('close-edit'))
        msg = parse.msg(self.link.read_msg())
        if msg[0] != 'success':
            self.link.send_msg(gen.error(1, 'client barfed'))
        else:
            self.link.send_msg(gen.success())

