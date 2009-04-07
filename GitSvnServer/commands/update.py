
import md5
import Queue
import threading

from GitSvnServer import parse, svndiff
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


def send_thread(link, inq, outq):
    m = inq.get()
    while m is not None:
        link.send_msg(*m)
        m = inq.get()
    outq.put(True)


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

    def get_prev_subpath_empty(self, path):
        for prev_path, (rev, start_empty) in self.prev_revs.items():
            if prev_path.startswith(path) and start_empty:
                return True
        return False

    def get_token(self, path):
        return 'tok%s' % md5.new(path).hexdigest()

    def send(self, *args):
        self.sendq.put(args)

    def update_dir(self, path, rev, want, props, contents, parent_token=None):
        repos = self.link.repos
        url = '/'.join((self.link.url, path))

        if '/' in want:
            want_head, want_tail = want.split('/', 1)
        else:
            want_head, want_tail = want, ''

        new_dir = True
        token = self.get_token(path)

        prev_rev, start_empty = self.get_prev(path)

        if prev_rev is None:
            new_dir = True
            prev_rev = None
        elif (prev_rev == rev or not repos.path_changed(url, rev, prev_rev)) \
                and not self.get_prev_subpath_empty(path):
            return
        else:
            stat = repos.stat(url, prev_rev)
            new_dir = stat[0] is None

        if parent_token is None:
            self.send(gen.tuple('open-root', gen.list(rev),
                                gen.string(token)))

            props = repos.get_props(url, rev)
            contents = contents[3]

        elif new_dir:
            self.send(gen.tuple('add-dir', gen.string(path),
                                gen.string(parent_token),
                                gen.string(token), '( )'))

            prev_rev = None

        else:
            self.send(gen.tuple('open-dir',
                                gen.string(path),
                                gen.string(parent_token),
                                gen.string(token),
                                gen.list(rev)))

        prev_props = {}
        if prev_rev is not None and not start_empty:
            for name, value in repos.get_props(url, prev_rev):
                prev_props[name] = value

        for name, value in props:
            if name in prev_props:
                if prev_props[name] == value:
                    del prev_props[name]
                    continue
                del prev_props[name]

            self.send(gen.tuple('change-dir-prop',
                                gen.string(token),
                                gen.string(name),
                                gen.list(gen.string(value))))

        for name in prev_props.keys():
            self.send(gen.tuple('change-dir-prop',
                                gen.string(token),
                                gen.string(name),
                                gen.list()))

        current_names = []
        for name, kind, props, content in contents:
            if len(want_head) > 0 and want_head != name:
                continue
            current_names.append(name)
            entry_path = name
            if len(path) > 0:
                entry_path = '/'.join((path, name))
            if kind == 'dir':
                self.update_dir(entry_path, rev, want_tail, props, content,
                                token)
            elif kind == 'file':
                self.update_file(entry_path, rev, props, content, token)
            else:
                raise foo

        if prev_rev is not None and not start_empty:
            for entry in repos.ls(url, prev_rev, include_changed=False):
                name, kind, size, last_rev, last_author, last_date = entry
                if len(want_head) > 0 and want_head != name:
                    continue
                if name not in current_names:
                    entry_path = name
                    if len(path) > 0:
                        entry_path = '/'.join((path, name))
                    self.send(gen.tuple('delete-entry',
                                        gen.string(entry_path),
                                        gen.list(prev_rev),
                                        gen.string(token)))

        self.send(gen.tuple('close-dir', gen.string(token)))

    def update_file(self, path, rev, props, contents, parent_token):
        repos = self.link.repos
        url = '/'.join((self.link.url, path))

        token = self.get_token(path)

        prev_rev, start_empty = self.get_prev(path)

        if prev_rev is None:
            prev_pl = []
            prev_contents = None
        elif prev_rev == rev or not repos.path_changed(url, rev, prev_rev):
            contents.close()
            return
        else:
            prev_rev, prev_pl, prev_contents = repos.get_file(url, prev_rev)

        new_file = prev_contents is None

        if new_file:
            self.send(gen.tuple('add-file', gen.string(path),
                                gen.string(parent_token),
                                gen.string(token), '( )'))

        else:
            self.send(gen.tuple('open-file', gen.string(path),
                                gen.string(parent_token),
                                gen.string(token),
                                gen.list(rev)))

        self.send(gen.tuple('apply-textdelta', gen.string(token), '( )'))

        diff_version = 0
        if 'svndiff1' in self.link.client_caps:
            diff_version = 1

        encoder = svndiff.Encoder(contents, version=diff_version)

        diff_chunk = encoder.get_chunk()
        count = 0
        while diff_chunk is not None:
            count += 1
            self.send(gen.tuple('textdelta-chunk',
                                gen.string(token),
                                gen.string(diff_chunk)))
            if count > 2:
                print "send chunk %d %d" % (count, len(diff_chunk))
            diff_chunk = encoder.get_chunk()
        csum = encoder.get_md5()

        if prev_contents:
            prev_contents.close()
        contents.close()

        self.send(gen.tuple('textdelta-end', gen.string(token)))

        prev_props = {}
        for name, value in prev_pl:
            prev_props[name] = value

        for name, value in props:
            if name in prev_props:
                if prev_props[name] == value:
                    del prev_props[name]
                    continue
                del prev_props[name]

            self.send(gen.tuple('change-file-prop',
                                gen.string(token),
                                gen.string(name),
                                gen.list(gen.string(value))))

        for name in prev_props.keys():
            self.send(gen.tuple('change-file-prop',
                                gen.string(token),
                                gen.string(name),
                                gen.list()))

        self.send(gen.tuple('close-file', gen.string(token),
                            gen.list(gen.string(csum))))

    @cmd_step
    def send_update(self):
        repos = self.link.repos

        depth = None
        send_copyfrom = False

        print "XX: %s" % self.args

        if len(self.args[0]) == 0:
            rev = repos.get_latest_rev()
        else:
            rev = int(self.args[0][0])
        path = parse.string(self.args[1])

        recurse = self.args[2] == 'true'

        if len(self.args) > 3:
            depth = self.args[3]
            send_copyfrom = parse.bool(self.args[4])

        self.link.send_msg(gen.tuple('target-rev', rev))

        self.sendq = Queue.Queue()
        self.waitq = Queue.Queue()

        thread = threading.Thread(target=send_thread,
                                  args=(self.link, self.sendq, self.waitq))
        thread.start()

        import time
        t1 = time.time()
        print "get contents"
        contents = repos.get_files(self.link.url, rev)
        t2 = time.time()
        print t2 - t1
        print "start sending"
        self.update_dir('', rev, path, [], contents)
        print "all sends now queued"
        t3 = time.time()
        print t3 - t2
        print t3 - t1

        self.sendq.put(None)
        print "wait for sending thread"
        self.waitq.get()

        print "send close-edit message"
        self.link.send_msg(gen.tuple('close-edit'))
        msg = parse.msg(self.link.read_msg())
        if msg[0] != 'success':
            errno = msg[1][0][0]
            errmsg = parse.string(msg[1][0][1])
            self.link.send_msg(gen.tuple('abort-edit'))
            self.link.send_msg(gen.error(errno, errmsg))
        else:
            self.link.send_msg(gen.success())
