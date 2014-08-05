import re
import time
import threading

import pygit2

from GitSvnServer.errors import ClientError
import generate as gen
import rwlock


def format_time(timestamp):
    return time.strftime('%Y-%m-%dT%H:%M:%S.000000Z', timestamp)


class Ref:
    def __init__(self, name, base_path, writeable):
        """
        :type name: str
        :type base_path: str
        :type writeable: bool
        """
        self.name = name
        self.base_path = base_path
        self.writeable = writeable
        self.latest_rev_lock = threading.Lock()

        self.revs = []
        """:type : list[RefRevision]"""

    def __cmp__(self, other):
        return cmp(self.base_path, other.base_path)

    def get_latest_rev(self):
        """
        :rtype : RefRevision
        """
        with self.latest_rev_lock:
            return self.revs[-1]

    def map_rev(self, rev):
        with self.latest_rev_lock:
            if rev is None:
                return self.revs[-1]

            if rev < 1 or rev > len(self.revs):
                return None

            return self.revs[rev - 1]


class DumbTreeEntry(object):
    def __init__(self, oid, filemode):
        self.id = oid
        self.filemode = filemode


class RefRevision(object):
    def __init__(self, number, commit, ref, prev, pygit):
        """
        :type number: int
        :type commit: pygit2.Commt | None
        :type ref: Ref | None
        :type prev: RefRevision | None
        :type pygit: pygit2.Repository | None
        """
        self.number = number
        self.commit = commit
        self.ref = ref
        self.prev = prev
        self._pygit = pygit

        self._changed_paths = None
        """:type : dict[str, str]"""

        self._changed_paths_lock = threading.Lock()

    def author(self):
        if self.commit is None:
            return None

        return self.commit.author.email

    def message(self):
        if self.commit is None:
            return ''
        return self.commit.raw_message

    def gen_author(self):
        author = self.author()
        if author is None:
            return gen.list()

        return gen.list(gen.string(author))

    def date(self):
        if self.commit is None:
            date = 0
        else:
            # TODO(marat): timezone?
            date = self.commit.author.time

        return format_time(time.gmtime(date))

    def gen_date(self):
        return gen.list(gen.string(self.date()))

    def find_file(self, path):
        """
        :rtype : TreeEntry | None
        :type path: str | None
        """
        if self.commit is None:
            return None

        if path is None:
            return DumbTreeEntry(self.commit.tree_id, pygit2.GIT_FILEMODE_TREE)

        try:
            return self.commit.tree[path]
        except KeyError:
            return None

    @staticmethod
    def _match_path(path, prefix, paths):
        for p in paths:
            path_prefix = '/'.join(filter(None, [prefix, p]))

            if path_prefix == '':
                return True

            if path == path_prefix:
                return True

            if path.startswith(path_prefix + '/'):
                return True

        return False

    def changed_paths(self, prefix, paths):
        """
        :type prefix: str
        :type paths: list[str]
        :rtype : dict[str, str]
        """
        with self._changed_paths_lock:
            if self._changed_paths is None:
                self._changed_paths = {}
                if self.commit:
                    if self.prev is None:
                        for f in self.commit.tree:
                            self._changed_paths[f.name] = 'A'
                    else:
                        # TODO(marat): full diff calculation is an overkill here actually
                        for patch in self.prev.commit.tree.diff_to_tree(self.commit.tree):
                            self._changed_paths[patch.new_file_path] = patch.status

                # yield execution for other threads
                time.sleep(0)

        result = {}

        for path, mode in self._changed_paths.items():
            match_path = self._match_path(path, prefix, paths)
            if match_path:
                result['/'.join([self.ref.base_path, path])] = mode

        return result

    def __cmp__(self, other):
        number_cmp = cmp(self.number, other.number)

        if number_cmp != 0:
            return number_cmp

        return cmp(self.ref, other.ref)


class FileInfo(object):
    def __init__(self, kind, last_change, repo_uuid, filemode, blob_id, pygit):
        """
        :type kind: str
        :type last_change: RefRevision
        :type repo_uuid: str
        :type pygit: pygit2.Repository
        """
        self.kind = kind
        self.last_change = last_change
        self.repo_uuid = repo_uuid
        self.filemode = filemode
        self.blob_id = blob_id
        self._pygit = pygit
        self._size = -1

    @property
    def size(self):
        if self._size < 0:
            if self.blob_id is None:
                self._size = 0
            else:
                self._size = self._pygit[self.blob_id].size

        return self._size

    def __eq__(self, other):
        if self.kind != other.kind:
            return False
        if self.size != other.size:
            return False

        if self.filemode != other.filemode:
            return False

        # TODO(marat): proper directory diff is required
        if self.blob_id is None or other.blob_id is None:
            return False

        # if self.blob is None:
        # return other.blob is None
        #
        # if other.blob is None:
        # return False

        return self.blob_id == other.blob_id

    def __ne__(self, other):
        return not self.__eq__(other)

    def props(self, include_internal_props=True):
        """
        :rtype : list[(str, str)]
        """
        if self.filemode == pygit2.GIT_FILEMODE_BLOB_EXECUTABLE:
            yield ('svn:executable', '*')
        elif self.filemode == pygit2.GIT_FILEMODE_LINK:
            yield ('svn:special', '*')

        if include_internal_props:
            yield ('svn:entry:uuid', self.repo_uuid)
            yield ('svn:entry:committed-rev', str(self.last_change.number))
            yield ('svn:entry:committed-date', self.last_change.date())

            if self.last_change.author is not None:
                yield ('svn:entry:last-author', self.last_change.author())


class LogEntry:
    def __init__(self, rev, changed_paths):
        """
        :type rev: RefRevision
        :type changed_paths: dict[str, str]
        """
        self.rev = rev
        self.changed_paths = changed_paths


class GetFilesEntry(object):
    def __init__(self, name, stat, children):
        """
        :type name: str
        :type stat: FileInfo
        :type children: [GetFilesEntry]
        """
        self.name = name
        self.stat = stat

        self.children = children
        """:type : [GetFilesEntry]"""


INITIAL_REVISION = RefRevision(0, None, None, None, None)
SPECIAL_DIRS = ['', 'tags', 'branches']
UPDATE_PERIOD_SECS = 10

TRUNK_RE = re.compile(r'^trunk(/(?P<path>.*))?$')
BRANCH_RE = re.compile(r'^branches/(?P<branch>[^/]+)(/(?P<path>.*))?$')
TAG_RE = re.compile(r'^tags/(?P<tag>[^/]+)(/(?P<path>.*))?$')


class CommitInfo(object):
    def __init__(self, repo, parent_rev):
        """
        :type repo: Repository
        :type parent_rev: RefRevision
        """
        self.repo = repo
        self.parent_rev = parent_rev.number
        self.parent_rev_sha = parent_rev.commit.oid


class Repository(object):
    def __init__(self, location, repo_uuid, users):
        """
        :type location: str
        :type repo_uuid: str
        """
        self.pygit = pygit2.Repository(location)
        self.users = users

        # This lock is used to prevent readers access when Updater changes refs
        lock = rwlock.RWLock()
        self.read_lock = rwlock.ReadLock(lock)
        self.write_lock = rwlock.WriteLock(lock)

        self.uuid = repo_uuid

        self.refs = {}
        """:type : dict[str, Ref]"""

        self.updater = Updater(self)
        self.updater.start()

    def get_latest_rev(self):
        """
        :rtype : int
        """
        return self._get_latest_rev().number

    def find_file(self, path, rev):
        """
        :type path: str
        :type rev: int | None
        :rtype : FileInfo | None
        """
        path, rev = self._map_args(path, rev)

        if rev.ref is None:
            if path in SPECIAL_DIRS:
                # TODO(marat): last_change_rev
                return FileInfo('dir', rev, self.uuid, pygit2.GIT_FILEMODE_TREE, None, self.pygit)
            else:
                return None

        entry = rev.find_file(path)

        if entry is None:
            return None

        # TODO(marat): last_change_rev
        if entry.filemode == pygit2.GIT_FILEMODE_TREE:
            return FileInfo('dir', rev, self.uuid, entry.filemode, None, self.pygit)

        return FileInfo('file', rev, self.uuid, entry.filemode, entry.id, self.pygit)

    def paths_different(self, path, rev, prev_path, prev_rev):
        f = self.find_file(path, rev)
        prev = self.find_file(prev_path, prev_rev)
        if f is None:
            return prev is not None

        if prev is None:
            return True

        return f != prev

    def ls(self, dir_path, rev):
        """
        :type dir_path: str
        :type rev: int | None
        :rtype : list[(str, StatResult)]
        """
        path, rev = self._map_args(dir_path, rev)
        if rev.ref is None:
            if path == '':
                yield ('branches', self.find_file('branches', None))
                yield ('tags', self.find_file('tags', None))

                trunk_stat = self.find_file('trunk', None)
                if trunk_stat is not None:
                    yield ('trunk', trunk_stat)

                return

            # /tags and /branches listing
            for ref in sorted(self.refs.values()):
                if ref.base_path.startswith('/' + path):
                    stat = self.find_file(ref.base_path, rev.number)
                    if stat:
                        yield (ref.base_path[(len(path) + 1):], stat)

            return

        entry = rev.find_file(path)
        if entry is None or entry.filemode != pygit2.GIT_FILEMODE_TREE:
            return

        for entry in self.pygit[entry.id]:
            yield (entry.name, self.find_file(dir_path + '/' + entry.name, rev.number))

    def log(self, path, target_paths, start_rev, end_rev, limit):
        """
        :type path: str | None
        :type target_paths: [str]
        :param start_rev: int | None
        :param end_rev: int | None
        :param limit: int
        :rtype : list[LogEntry]
        """
        path, rev = self._map_args(path, max(start_rev, end_rev))
        if rev.ref is None:
            return

        left = limit
        while rev is not None and rev.number >= min(start_rev, end_rev):
            changed_paths = rev.changed_paths(path, target_paths)

            if changed_paths:
                yield LogEntry(rev, changed_paths)

                if limit > 0:
                    left -= 1
                    if left < 0:
                        break

            rev = rev.prev

    def get_props(self, path, rev, include_internal_props=True):
        """
        :type path: str | None
        :type rev: int | None
        :rtype : list[(str, str)]
        """
        stat = self.find_file(path, rev)
        if stat is None:
            return []

        return stat.props(include_internal_props)

    def get_files(self, path, rev):
        """
        :type path: str | None
        :type rev: int | None
        :rtype : GetFilesEntry
        """
        stat = self.find_file(path, rev)
        if stat is None:
            return None

        children = self._get_files_r(path, rev)
        return GetFilesEntry(path, stat, children)

    def _get_files_r(self, path, rev):
        """
        :type path: str
        :type rev: int | None
        :rtype : list[GetFilesEntry]
        """
        result = []

        for name, stat in self.ls(path, rev):
            if stat.kind == 'dir':
                children = self._get_files_r('/'.join(filter(None, [path, name])), rev)
            else:
                children = []

            result.append(GetFilesEntry(name, stat, children))

        return result

    def _get_latest_rev(self):
        if self.refs:
            # TODO(marat): refs deletion
            return max([ref.get_latest_rev() for ref in self.refs.values()])
        else:
            return INITIAL_REVISION

    def start_commit(self):
        return CommitInfo(self, self._get_latest_rev())

    def complete_commit(self, commit_info, msg, root, user):
        """
        :type commit_info: CommitInfo
        :type msg: str
        :type user: GitSvnServer.config.User
        :type root: GitSvnServer.commands.commit.Dir
        :rtype : RefRevision
        """
        path, rev = self._map_args(root.full_path, commit_info.parent_rev)

        if rev.ref is None:
            # TODO(marat): tag/branch creation/deletion
            raise ClientError("Tag/branch creation/deletion is not supported yet")

        if not rev.ref.writeable:
            raise ClientError("%s is not writeable" % rev.ref.base_path)

        author = pygit2.Signature(user.name, user.email)

        # TODO: tree
        tree = tree = self.pygit.TreeBuilder()

        # TODO(marat): should we cache sha1 in Commit#get_edits?
        parent_commit = rev.ref.revs[commit_info.parent_rev - 1].commit.oid

        oid = self.pygit.create_commit(None, author, author, msg, tree.write(), [parent_commit])

        # TODO: arg escaping
        print "git --git-dir=%s push --porcelain . %s:%s" % (self.pygit.path, oid, rev.ref.name)

        # TODO: retval
        return None

    def _map_args(self, path, rev):
        """
        :param path: str | None
        :param rev: int | None
        :rtype : (str, RefRevision)
        """
        trunk_m = TRUNK_RE.search(path)
        branch_m = BRANCH_RE.search(path)
        tag_m = TAG_RE.search(path)

        ref = None
        ref_path = None

        if trunk_m:
            ref, ref_path = 'refs/heads/master', trunk_m.group('path')
        elif branch_m:
            ref, ref_path = 'refs/heads/%s' % branch_m.group('branch'), branch_m.group('path')
        elif tag_m:
            ref, ref_path = 'refs/tags/%s' % tag_m.group('tag'), tag_m.group('path')

        ref = self.refs.get(ref, None)
        if ref is None:
            latest = self._get_latest_rev()
            # Yes, path instead of ref_path
            return path, RefRevision(latest.number, latest.commit, None, latest.prev, self.pygit)

        rev = ref.map_rev(rev)

        if rev is None:
            latest = self._get_latest_rev()
            # Yes, path instead of ref_path
            return path, RefRevision(latest.number, latest.commit, None, latest.prev, self.pygit)

        return ref_path, rev


class Updater(object):
    def __init__(self, repo):
        """
        :type repo: Repository
        """
        self.repo = repo
        # This lock is required to prevent Updater + force_sync interfere during commit
        self.lock = threading.Lock()

    def start(self):
        self._dosync()

        t = threading.Thread(target=self.sync, name="Repository updater: %s" % self.repo.pygit.path)
        t.daemon = True
        t.start()

    def _append_history(self, commits, latest, ref):
        for idx, commit in enumerate(commits):
            latest = RefRevision(len(ref.revs) + 1, commit, ref, latest, self.repo.pygit)
            ref.revs.append(latest)

    def _sync_ref(self, ref_name):
        writeable = True
        if ref_name == 'refs/heads/master':
            base_path = '/trunk'
        elif ref_name.startswith('refs/heads/'):
            base_path = '/branches/' + ref_name[11:]
        elif ref_name.startswith('refs/tags/'):
            base_path = '/tags/' + ref_name[10:]
            writeable = False
        else:
            return

        try:
            head = self.repo.pygit.lookup_reference(ref_name).get_object()
        except KeyError:
            # Ref could be deleted between listall_references and lookup_reference. Oh my.
            return

        ref = self.repo.refs.get(ref_name)
        if ref is None:
            ref = Ref(ref_name, base_path, writeable)
            old_head = None
        else:
            old_head = ref.get_latest_rev()

        t = time.time()
        commits = []

        continuation = False
        while True:
            if old_head is not None and head.oid == old_head.commit.oid:
                continuation = True
                break

            commits.append(head)
            if not head.parents:
                break

            head = head.parents[0]

        commits.reverse()

        if not commits:
            return

        if old_head is None:
            self._append_history(commits, None, ref)
            with self.repo.write_lock:
                self.repo.refs[ref_name] = ref
        elif continuation:
            with ref.latest_rev_lock:
                self._append_history(commits, old_head, ref)
        else:
            print "WARNING! History rewrite of %s. %s cannot be found via first-parent traversal from %s" \
                  % (ref_name, old_head.commit.oid, commits[0].oid)

            # TODO(marat): do we actually need to hold latest_rev_lock here?
            with self.repo.write_lock, ref.latest_rev_lock:
                del ref.revs[:]
                self._append_history(commits, None, ref)

        print "Loaded %s commits on %s in %s seconds" % (len(commits), ref_name, time.time() - t)

    def _dosync(self):
        with self.lock:
            # TODO(marat): refs deletion
            for ref_name in self.repo.pygit.listall_references():
                # TODO(marat): until we have stable revision number generation, we cannot support multiple branches
                if ref_name == 'refs/heads/master':
                    self._sync_ref(ref_name)

    def sync(self):
        while True:
            time.sleep(UPDATE_PERIOD_SECS)
            self._dosync()
