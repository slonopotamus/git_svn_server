
import generate as gen
import md5
import parse
import svndiff

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

    def get_token(self, path):
        return 'tok%s' % path

    def update_dir(self, path, rev, parent_token=None):
        repos = self.link.repos
        url = '/'.join((self.link.url, path))

        new_dir = True
        token = self.get_token(path)

        if parent_token is None:
            self.link.send_msg(gen.tuple('open-root', gen.list(rev),
                                         gen.string(token)))

            if new_dir:
                for name, value in repos.get_props(url, rev):
                    self.link.send_msg(gen.tuple('change-dir-prop',
                                                 gen.string(token),
                                                 gen.string(name),
                                                 gen.list(gen.string(value))))

        elif new_dir:
            self.link.send_msg(gen.tuple('add-dir', gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token), '( )'))

            for name, value in repos.get_props(url, rev):
                self.link.send_msg(gen.tuple('change-dir-prop',
                                             gen.string(token),
                                             gen.string(name),
                                             gen.list(gen.string(value))))

        else:
            self.link.send_msg(gen.tuple('open-dir', gen.string(parent_token),
                                         gen.string(token), rev))

        for entry in repos.ls(url, rev):
            print entry
            name, kind, size, last_rev, last_author, last_date = entry
            if len(path) == 0:
                entry_path = name
            else:
                entry_path = '/'.join((path, name))
            if kind == 'dir':
                self.update_dir(entry_path, rev, token)
            elif kind == 'file':
                self.update_file(entry_path, rev, token)
            else:
                raise foo

        self.link.send_msg(gen.tuple('close-dir', gen.string(token)))

    def update_file(self, path, rev, parent_token):
        repos = self.link.repos
        url = '/'.join((self.link.url, path))

        new_file = True
        token = self.get_token(path)

        if new_file:
            self.link.send_msg(gen.tuple('add-file', gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token), '( )'))

            rev, props, contents = repos.get_file(url, rev)

            for name, value in props:
                self.link.send_msg(gen.tuple('change-file-prop',
                                             gen.string(token),
                                             gen.string(name),
                                             gen.list(gen.string(value))))

            self.link.send_msg(gen.tuple('apply-textdelta', gen.string(token),
                                         '( )'))

            self.link.send_msg(gen.tuple('textdelta-chunk',
                                         gen.string(token),
                                         gen.string(svndiff.header())))

            m = md5.new()
            data = contents.read(8192)
            while len(data) > 0:
                m.update(data)
                diff_chunk = svndiff.encode_new(data)
                self.link.send_msg(gen.tuple('textdelta-chunk',
                                             gen.string(token),
                                             gen.string(diff_chunk)))
                data = contents.read(8192)
            csum = m.hexdigest()

            self.link.send_msg(gen.tuple('textdelta-end', gen.string(token)))

        else:
            self.link.send_msg(gen.tuple('open-file', gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token), rev))


        self.link.send_msg(gen.tuple('close-file', gen.string(token),
                                     gen.tuple(gen.string(csum))))

    @cmd_step
    def send_update(self):
        repos = self.link.repos

        print "XX: %s" % self.args

        if len(self.args[0]) == 0:
            rev = repos.get_latest_rev()
        else:
            rev = int(self.args[0][0])
        path = parse.string(self.args[1])
        recurse = self.args[2] == 'true'

        url = '/'.join((self.link.url, path))

        self.link.send_msg(gen.tuple('target-rev', rev))

        self.update_dir(path, rev)

        print "ought to be doing the edit bits here ..."
        self.link.send_msg(gen.tuple('close-edit'))
        msg = parse.msg(self.link.read_msg())
        if msg[0] != 'success':
            self.link.send_msg(gen.error(1, 'client barfed'))
        else:
            self.link.send_msg(gen.success())
