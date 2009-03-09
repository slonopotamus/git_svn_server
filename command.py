
import generate as gen
import parse

from cmd_base import *

def process(link):
    msg = parse.msg(link.read_msg())

    command = msg[0]
    args = msg [1]

    if command not in commands:
        link.send_msg(gen.error(210001, "Unknown command '%s'" % command))
        return None

    print "found %s %s" % (command, commands[command](link, args))

    return commands[command](link, args)

class LatestRev(SimpleCommand):
    _cmd = 'get-latest-rev'

    def do_cmd(self):
        repos = self.link.repos

        latest_rev = repos.get_latest_rev()

        self.link.send_msg(gen.success(latest_rev))

class CheckPath(SimpleCommand):
    _cmd = 'check-path'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args[0])
        if len(path) > 0:
            url = '/'.join((url, path))

        if len(args) > 1:
            rev = int(args[1][0])

##        ref, path = repos.parse_url(url)

##        print "ref: %s" % ref
##        print "path: %s" % path
##        print "rev: %s" % rev

        type = repos.check_path(url, rev)

        self.link.send_msg(gen.success(type))

class Stat(SimpleCommand):
    _cmd = 'stat'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args[0])
        if len(path) > 0:
            url = '/'.join((url, path))

        if len(args) > 1:
            rev = int(args[1][0])

##        ref, path = repos.parse_url(url)

##        print "ref: %s" % ref
##        print "path: %s" % path
##        print "rev: %s" % rev

        path, kind, size, changed, by, at = repos.stat(url, rev)

        if path is None:
            self.link.send_msg(gen.success(gen.list()))

        else:
            ls_data = gen.list(kind,
                               size,
                               'false', # has-props
                               changed,
                               gen.list(gen.string(at)),
                               gen.list(gen.string(by)))

            self.link.send_msg(gen.success(gen.list(ls_data)))

class GetDir(SimpleCommand):
    _cmd = 'get-dir'

    def do_cmd(self):
        repos = self.link.repos
        args = self.args
        url = self.link.url
        rev = None

        path = parse.string(args.pop(0))
        if len(path) > 0:
            url = '/'.join((url, path))

        arg = args.pop(0)
        if len(arg) > 0:
            rev = int(arg[0])

        want_props = parse.bool(args.pop(0))

        want_contents = parse.bool(args.pop(0))

        fields = []
        if len(args) > 0:
            fields = args[0]

##        ref, path = repos.parse_url(url)

##        print "ref: %s" % ref
##        print "path: %s" % path
##        print "rev: %s" % rev
##        print "want_props: %s" % want_props
##        print "want_contents: %s" % want_contents
##        print "fields: %s" % fields

        ls_data = []

        for path, kind, size, changed, by, at in repos.ls(url, rev):
            ls_data.append(gen.list(gen.string(path),
                                    kind,
                                    size,
                                    'false', # has-props
                                    changed,
                                    gen.list(gen.string(at)),
                                    gen.list(gen.string(by))))

        response = "%d ( ) %s" % (rev, gen.list(*ls_data))

        self.link.send_msg(gen.success(response))

class Log(SimpleCommand):
    _cmd = 'log'

    def do_cmd(self):
        repos = self.link.repos
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
        if len(arg) > 0:
            end_rev = int(arg[0])
            if end_rev == 0:
                end_rev = 1

        send_changed_paths = parse.bool(args.pop(0))

        strict_node = parse.bool(args.pop(0))

        limit = 0
        if len(args) > 0:
            limit = int(args.pop(0))

        include_merged_revisions = False
        if len(args) > 0:
            include_merged_revisions = parse.bool(args.pop(0))

        # all-revprops | revprops

        # ( revprop:string ... )

        for changes, rev, author, date, msg, has_children, revprops in repos.log(url, target_paths, start_rev, end_rev, limit):
            changed_paths = []
            if send_changed_paths:
                for path, change, copy_path, copy_rev in changes:
                    cp = gen.list()
                    if copy_path is not None and copy_rev is not None:
                        cp = gen.list(gen.string(copy_path), copy_rev)
                    changed_paths.append(gen.list(gen.string(path),
                                                  change, cp, gen.list()))
                                                  #change, cp, cr, gen.list()))
            log_entry = gen.list(gen.list(*changed_paths),
                                 rev,
                                 gen.list(gen.string(author)),
                                 gen.list(gen.string(date)),
                                 gen.list(gen.string(msg)))
            self.link.send_msg(log_entry)

        self.link.send_msg('done')

        self.link.send_msg(gen.success())

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
