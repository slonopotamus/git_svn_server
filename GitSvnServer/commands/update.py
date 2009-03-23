
import md5

from GitSvnServer import parse, svndiff
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *

class Update(Command):
    _cmd = 'update'

    def report_set_path(self, path, rev, start_empty, lock_token, depth):
        self.prev_revs[path] = (rev, start_empty)
        print "report: set path - %s %d %s" % (path, rev, start_empty)

    def report_link_path(self, path, url, rev, start_empty, lock_token, depth):
        print "report: link path"

    def report_delete_path(self, path):
        print "report: delete path"

    @cmd_step
    def auth(self):
        raise ChangeMode('auth', 'command')

    @cmd_step
    def get_reports(self):
        self.prev_revs = {'' : (None, True)}
        raise ChangeMode('report')

    def get_parent_path(self, path):
        if '/' in path:
            parent_path, a = path.rsplit('/', 1)
        else:
            parent_path = ''

        return parent_path

    def get_prev(self, path):
        if path in self.prev_revs:
            return self.prev_revs[path]

        parent_path = self.get_parent_path(path)
        while parent_path not in self.prev_revs:
            parent_path = self.get_parent_path(parent_path)

        rev, start_empty = self.prev_revs[parent_path]

        if start_empty:
            return None, True

        return rev, start_empty

    def get_token(self, path):
        return 'tok%s' % md5.new(path).hexdigest()

    def update_dir(self, path, rev, parent_token=None):
        repos = self.link.repos
        url = '/'.join((self.link.url, path))

        new_dir = True
        token = self.get_token(path)

        prev_rev, start_empty = self.get_prev(path)

        if prev_rev is None:
            new_dir = True
            prev_rev = None
        elif prev_rev is not None:
            stat = repos.stat(url, prev_rev)
            new_dir = stat[0] is None

        if parent_token is None:
            self.link.send_msg(gen.tuple('open-root', gen.list(rev),
                                         gen.string(token)))

        elif new_dir:
            self.link.send_msg(gen.tuple('add-dir', gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token), '( )'))

            prev_rev = None

        else:
            self.link.send_msg(gen.tuple('open-dir',
                                         gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token),
                                         gen.list(rev)))

        prev_props = {}
        if prev_rev is not None:
            for name, value in repos.get_props(url, prev_rev):
                prev_props[name] = value

        for name, value in repos.get_props(url, rev):
            if name in prev_props:
                if prev_props[name] == value:
                    del prev_props[name]
                    continue
                del prev_props[name]

            self.link.send_msg(gen.tuple('change-dir-prop',
                                         gen.string(token),
                                         gen.string(name),
                                         gen.list(gen.string(value))))

        for name in prev_props.keys():
            self.link.send_msg(gen.tuple('change-dir-prop',
                                         gen.string(token),
                                         gen.string(name),
                                         gen.list()))

        for entry in repos.ls(url, rev):
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

        token = self.get_token(path)

        prev_rev, start_empty = self.get_prev(path)

        if prev_rev is None:
            prev_pl = []
            prev_contents = None
        elif prev_rev == rev:
            return
        else:
            prev_rev, prev_pl, prev_contents = repos.get_file(url, prev_rev)

        new_file = prev_contents is None

        rev, props, contents = repos.get_file(url, rev)

        if new_file:
            self.link.send_msg(gen.tuple('add-file', gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token), '( )'))

        else:
            self.link.send_msg(gen.tuple('open-file', gen.string(path),
                                         gen.string(parent_token),
                                         gen.string(token),
                                         gen.list(rev)))

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

        if prev_contents:
            prev_contents.close()
        contents.close()

        self.link.send_msg(gen.tuple('textdelta-end', gen.string(token)))

        prev_props = {}
        for name, value in prev_pl:
            prev_props[name] = value

        for name, value in props:
            if name in prev_props:
                if prev_props[name] == value:
                    del prev_props[name]
                    continue
                del prev_props[name]

            self.link.send_msg(gen.tuple('change-file-prop',
                                         gen.string(token),
                                         gen.string(name),
                                         gen.list(gen.string(value))))

        for name in prev_props.keys():
            self.link.send_msg(gen.tuple('change-file-prop',
                                         gen.string(token),
                                         gen.string(name),
                                         gen.list()))

        self.link.send_msg(gen.tuple('close-file', gen.string(token),
                                     gen.list(gen.string(csum))))

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
