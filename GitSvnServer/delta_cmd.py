import Queue
from cStringIO import StringIO
import threading

from GitSvnServer import parse, svndiff
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5


def send_thread(link, inq, outq):
    m = inq.get()
    try:
        while m is not None:
            link.send_msg(*m)
            m = inq.get()
        outq.put(True)
    except Exception as e:
        outq.put(e)


class DeltaCmd(Command):
    def report_set_path(self, path, rev, start_empty, lock_token, depth):
        self.prev_revs[path] = (rev, start_empty)

    def report_link_path(self, path, url, rev, start_empty, lock_token, depth):
        raise NotImplementedError()

    def report_delete_path(self, path):
        self.deleted_paths.append(path)

    # noinspection PyMethodMayBeStatic
    def auth(self):
        raise ChangeMode('auth', 'command')

    def get_reports(self):
        self.setup()
        raise ChangeMode('report')

    @staticmethod
    def get_parent_path(path):
        if '/' in path:
            parent_path, a = path.rsplit('/', 1)
        else:
            parent_path = ''

        return parent_path

    def get_prev(self, path):
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

    @staticmethod
    def get_token(path):
        return 'tok%s' % md5(path).hexdigest()

    def send(self, *args):
        if not self.waitq.empty():
            raise self.waitq.get()
        self.sendq.put(args)

    def update_dir(self, path, rev, want, entry, parent_token=None):
        """
        :type path: str
        :type entry: GitSvnServer.repository.GetFilesEntry
        :type rev: int | None
        """
        repo = self.link.repo
        url = '/'.join([self.link.url, path]).rstrip('/')
        newurl = '/'.join([self.newurl, path]).rstrip('/')

        if '/' in want:
            want_head, want_tail = want.split('/', 1)
        else:
            want_head, want_tail = want, ''

        token = self.get_token(path)

        prev_rev, start_empty = self.get_prev(path)

        if prev_rev is None:
            new_dir = True
        elif not self.get_prev_subpath_empty(path) and not repo.paths_different(newurl, rev, url, prev_rev):
            return
        else:
            new_dir = repo.find_file(url, prev_rev) is None

        if parent_token is None:
            self.send(gen.tuple('open-root', gen.list(rev), gen.string(token)))
        elif new_dir:
            self.send(gen.tuple('add-dir', gen.string(path),
                                gen.string(parent_token),
                                gen.string(token), gen.list()))
            prev_rev = None
        else:
            self.send(gen.tuple('open-dir',
                                gen.string(path),
                                gen.string(parent_token),
                                gen.string(token),
                                gen.list(rev)))

        if prev_rev is not None and not start_empty:
            prev_props = dict(repo.get_props(url, prev_rev))
        else:
            prev_props = {}

        for name, value in entry.stat.props():
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
        for child in entry.children:
            if len(want_head) > 0 and want_head != child:
                continue
            current_names.append(child.name)
            entry_path = child.name
            if len(path) > 0:
                entry_path = '/'.join((path, child.name))

            if child.stat.kind == 'dir':
                self.update_dir(entry_path, rev, want_tail, child, token)
            elif child.stat.kind == 'file':
                self.update_file(entry_path, rev, child, token)

        if prev_rev is not None and not start_empty:
            for name, stat in repo.ls(url, prev_rev):
                if len(want_head) > 0 and want_head != name:
                    continue
                if name not in current_names:
                    entry_path = name
                    if len(path) > 0:
                        entry_path = '/'.join((path, name))
                    if entry_path in self.deleted_paths:
                        continue
                    self.send(gen.tuple('delete-entry',
                                        gen.string(entry_path),
                                        gen.list(prev_rev),
                                        gen.string(token)))

        self.send(gen.tuple('close-dir', gen.string(token)))

    def update_file(self, path, rev, entry, parent_token):
        """

        :type path: str
        :type rev: int
        :type entry: GitSvnServer.repository.GetFilesEntry
        """
        repo = self.link.repo

        url = '/'.join((self.link.url, path))
        contents = StringIO(self.link.repo.pygit[entry.stat.blob_id].data)
        newurl = '/'.join((self.newurl, path))

        token = self.get_token(path)

        prev_rev, start_empty = self.get_prev(path)

        if prev_rev is None:
            prev_pl = []
            prev_contents = None
        elif not repo.paths_different(newurl, rev, url, prev_rev):
            return
        else:
            prev_stat = repo.find_file(url, prev_rev)
            if prev_stat and prev_stat.blob_id is not None:
                prev_pl = prev_stat.props()
                prev_contents = StringIO(self.link.repo.pygit[prev_stat.blob_id].data)
            else:
                prev_pl = {}
                prev_contents = None

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

        # TODO(marat): compression eats tons of CPU
        # if 'svndiff1' in self.link.client_caps:
        # diff_version = 1

        encoder = svndiff.Encoder(contents, prev_contents, version=diff_version)

        diff_chunk = encoder.get_chunk()
        while diff_chunk is not None:
            self.send(gen.tuple('textdelta-chunk',
                                gen.string(token),
                                gen.string(diff_chunk)))
            diff_chunk = encoder.get_chunk()
        csum = encoder.get_md5()

        if prev_contents:
            prev_contents.close()
        contents.close()

        self.send(gen.tuple('textdelta-end', gen.string(token)))

        prev_props = {}
        for name, value in prev_pl:
            prev_props[name] = value

        for name, value in entry.stat.props():
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

    def do_complete(self):
        return self.complete()

    def __init__(self, link, args):
        Command.__init__(self, link, args)
        self.steps = [
            DeltaCmd.auth,
            DeltaCmd.get_reports,
            DeltaCmd.do_complete,
        ]

        self.newurl = None
        self.prev_revs = {'': (None, True)}
        self.deleted_paths = []

        self.sendq = Queue.Queue()
        self.waitq = Queue.Queue()

    def setup(self):
        raise NotImplementedError()

    def complete(self):
        raise NotImplementedError()

    def send_response(self, path, url, rev):
        repo = self.link.repo

        thread = threading.Thread(target=send_thread, args=(self.link, self.sendq, self.waitq))
        thread.start()
        try:
            with repo.read_lock:
                if rev is None:
                    rev = self.link.repo.get_latest_rev()
                self.send(gen.tuple('target-rev', rev))
                contents = repo.get_files(url, rev)
                self.update_dir('', rev, path, contents)
        finally:
            self.sendq.put(None)

        self.waitq.get()

        self.link.send_msg(gen.tuple('close-edit'))
        msg = parse.msg(self.link.read_msg())
        if msg[0] != 'success':
            errno = msg[1][0][0]
            errmsg = parse.string(msg[1][0][1])
            self.link.send_msg(gen.tuple('abort-edit'))
            self.link.send_msg(gen.error(errno, errmsg))
        else:
            self.link.send_msg(gen.success())
