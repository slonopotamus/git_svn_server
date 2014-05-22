from multiprocessing import Lock
from email.utils import parseaddr
import json
import re
import time
import uuid

from GitSvnServer.errors import *
from cat_file import *
from data import *
from db import *


def format_time(timestamp):
    return time.strftime('%Y-%m-%dT%H:%M:%S.000000Z', timestamp)


class GitFile(object):
    def __init__(self, commit=None, path=None, location=None):
        self.commit = commit
        self.path = path
        if location is None:
            location = commit.repos.config.location
        cmd = '--bare hash-object -w --stdin'
        self.hash_object = GitData(location, cmd)

    def write(self, data):
        self.hash_object.write(data)

    def close(self):
        self.hash_object.close_stdin()
        sha1 = self.hash_object.read().strip()
        self.hash_object.close()
        if self.commit is not None:
            self.commit.file_complete(self.path, sha1)
        return sha1


class GitCommit(object):
    def __init__(self, repos, url, ref, parent, prefix, user):
        """

        :type user: User
        """
        self.repos = repos
        self.url = url
        self.ref = ref
        self.parent = parent
        self.prefix = prefix
        self.dirs = {}
        self.files = {}
        self.user = user

    def remove_path(self, path):
        self.files.setdefault(path, {})['delete'] = True

    def add_dir(self, path, original=(None, None)):
        self.dirs.setdefault(path, {})['url'] = original[0]
        self.dirs.setdefault(path, {})['rev'] = original[1]

    def open_dir(self, path, rev=None):
        self.dirs.setdefault(path, {})

    def file_complete(self, path, sha1):
        self.files.setdefault(path, {})['sha1'] = sha1

    def modify_file(self, path, rev=None):
        if rev is not None:
            sha1 = self.repos.map.find_commit(self.ref, rev)
            if self.repos._path_changed(sha1, self.parent, path):
                raise PathChanged(path)
        if len(self.prefix) > 0:
            path = '/'.join((self.prefix, path))
        return GitFile(self, path)

    def set_file_prop(self, path, name, value):
        self.files.setdefault(path, {}).setdefault('props', {})[name] = value

    def set_dir_prop(self, path, name, value):
        self.dirs.setdefault(path, {}).setdefault('props', {})[name] = value


class GitError(Exception):
    pass


trunk_re = re.compile(r'^trunk(/(?P<path>.*))?$')
branch_re = re.compile(r'^branches/(?P<branch>[^/]+)(/(?P<path>.*))?$')
tag_re = re.compile(r'^tags/(?P<tag>[^/]+)(/(?P<path>.*))?$')
other_re = re.compile(r'^(?P<path>.*)$')


class Git(object):
    def __init__(self, location, uuid, users):
        self.users = users
        self.map = GitMap(self, location)
        self.lock = Lock()
        self.location = location
        self.cat_file = GitCatFile(self.location)
        self.created_date = format_time(time.gmtime(0))
        self.uuid = uuid

    def __get_git_data(self, command_string):
        git_data = GitData(self.location, command_string)

        git_data.open()

        data = [line.strip('\n') for line in git_data._data]

        error = git_data._err.read()
        if len(error) > 0:
            raise GitError(error)

        git_data.close()

        return data

    def __map_url(self, url):
        if url == '':
            return (None, '')

        trunk_m = trunk_re.search(url)
        branch_m = branch_re.search(url)
        tag_m = tag_re.search(url)
        other_m = other_re.search(url)

        if trunk_m:
            path = trunk_m.group('path')
            ref = 'refs/heads/master'
        elif branch_m:
            branch = branch_m.group('branch')
            path = branch_m.group('path')
            ref = 'refs/heads/%s' % branch
        elif tag_m:
            tag = tag_m.group('tag')
            path = tag_m.group('path')
            ref = 'refs/tags/%s' % tag
        elif other_m:
            path = other_m.group('path')
            ref = None
        else:
            raise foo

        if path == None:
            path = ''

        return (ref, path)

    def __map_type(self, type):
        if type is None:
            return 'none'

        if type == 'blob':
            return 'file'

        if type == 'tree':
            return 'dir'

    def get_latest_rev(self):
        return self.map.get_latest_rev()

    def __get_object(self, sha1, indep=False):
        return self.cat_file.get_object(sha1, indep)

    def __list_tags(self):
        return self.__get_git_data('tag -l')

    def __list_branches(self):
        refs = self.__get_git_data('for-each-ref --format="%(refname)" refs/heads')
        return [x[11:] for x in refs if x.startswith('refs/heads/')]

    def __ls_tree(self, sha1, path, options=''):
        results = []

        if not sha1:
            return results

        cmd = 'ls-tree -l %s %s "%s"' % (options, sha1, path)

        for line in self.__get_git_data(cmd):
            stat, git_path = line.split('\t', 1)
            mode, type, sha, size = stat.split()
            if size == '-':
                size = 0
            results.append((mode, type, sha, int(size), git_path))

        return results

    def __log(self, sha1, path, pretty=None, format=None, options=''):
        if pretty is not None:
            options = '%s "--pretty=%s"' % (options, pretty)

        elif format is not None:
            options = '%s "--pretty=format:%s"' % (options, format)

        cmd = 'log %s %s -- %s' % (options, sha1, path)

        return self.__get_git_data(cmd)

    def __rev_list(self, sha1, path, count=None):
        results = []

        c = ""
        if count is not None:
            c = "-n %d" % count
        cmd = 'rev-list %s %s -- %s' % (c, sha1, path)

        for line in self.__get_git_data(cmd):
            results.append(line.strip())

        return results

    def __commit_info(self, sha1):
        parents = []

        obj = self.__get_object(sha1)
        data = obj.read().split('\n')
        obj.close()

        c = 0
        for line in data:
            c += 1
            if line == '':
                break
            elif line.startswith('tree'):
                tree = line[4:].strip()
            elif line.startswith('parent'):
                parents.append(line[6:].strip())
            elif line.startswith('author'):
                author = line[6:-16].strip()
                name, email = parseaddr(author)
                when = int(line[-16:-6].strip())
                tz = int(line[-5:].strip())

        msg = '\n'.join(data[c:])

        tz_secs = 60 * (60 * (tz / 100) + (tz % 100))

        date = format_time(time.gmtime(when + tz_secs))

        return tree, parents, name, email, date, msg

    def __tag_info(self, sha1):
        parents = []

        obj = self.__get_object(sha1)
        data = obj.read()
        obj.close()

        c = 0
        for line in data.split('\n'):
            c += 1
            if line == '':
                break
            elif line.startswith('object'):
                obj = line[6:].strip()
            elif line.startswith('type'):
                type = line[4:].strip()
            elif line.startswith('tagger'):
                author = line[6:-16].strip()
                name, email = parseaddr(author)
                when = int(line[-16:-6].strip())
                tz = int(line[-5:].strip())
            elif line.startswith('tag'):
                tag_name = line[3:].strip()

        msg = '\n'.join(data[c:])

        tz_secs = 60 * (60 * (tz / 100) + (tz % 100))

        date = format_time(time.gmtime(when + tz_secs))

        return obj, type, tag_name, name, email, date, msg

    def __get_file_contents(self, mode, sha, indep_contents=False):
        contents = self.__get_object(sha, indep_contents)

        if mode == '120000':
            link = 'link %s' % contents.read()
            contents.close()
            contents = FakeData(link)

        return contents

    def __get_last_changed(self, sha1, path, rev=None):
        if sha1 is None:
            return rev, None, self.created_date

        changed_shas = self.__rev_list(sha1, path, count=1)

        if len(changed_shas) != 1:
            raise foo
        else:
            last_commit = changed_shas[0]
            ref, changed = self.map.get_ref_rev(last_commit)
            t, p, n, by, at, m = self.__commit_info(last_commit)

        return changed, by, at

    def __get_tag_changed(self, sha1):
        ref, changed = self.map.get_ref_rev(sha1)
        o, t, tn, n, by, at, m = self.__tag_info(sha1)

        return changed, by, at

    def __get_changed_paths(self, sha1, path=''):
        cmd = 'diff-tree --name-status -r %s^ %s -- %s' % (sha1, sha1, path)

        changed_files = {}
        for line in self.__get_git_data(cmd):
            change, path = line.split('\t', 1)
            changed_files[path] = change

        return changed_files

    def __translate_special(self, sha1):
        mode, sha = '', None

        obj = self.__get_object(sha1)
        data = obj.read()
        obj.close()

        if data.startswith('link '):
            mode = '120000'
            cmd = '--bare hash-object -w --stdin'
            ho = GitData(self.location, cmd)
            ho.write(data[5:])
            ho.close_stdin()
            sha = ho.read().strip()
            ho.close()

        return mode, sha

    def __get_svn_props(self, mode):
        props = []

        if mode == '120000':
            props.append(('svn:special', '*'))
        elif mode == '100755':
            props.append(('svn:executable', '*'))

        return props

    def __svn_internal_props(self, changed, by, at):
        props = []

        props.append(('svn:entry:uuid', self.uuid))
        props.append(('svn:entry:committed-rev', str(changed)))
        props.append(('svn:entry:committed-date', at))

        if by:
            props.append(('svn:entry:last-author', by))

        return props

    def _path_changed(self, sha1, sha2, path):
        cmd = 'diff-tree -r --name-only %s %s -- %s' % (sha1, sha2, path)
        changes = self.__get_git_data(cmd)

        return len(changes) != 0

    def check_path(self, url, rev):
        ref, path = self.__map_url(url)

        # Deal with the pseudo dirs at the top of the url space.  By adding the
        # name trunk to the URL it should be turned into somthing that __map_url
        # can map - either refs/tags/trunk (url was /tags), refs/heads/trunk
        # (url was /branches), or refs/heads/master (url was /).
        if ref is None:
            ref, path = self.__map_url("/".join((url, 'trunk')))
            if ref is not None and path == '':
                return 'dir'
            return 'none'

        sha1 = self.map.find_commit(ref, rev)

        if sha1 is None:
            return 'none'

        if path == '':
            return 'dir'

        data = self.__ls_tree(sha1, path)

        if len(data) != 1:
            return 'none'

        return self.__map_type(data[0][1])

    def __stat_tags_dir(self, rev):
        sha1 = self.map.get_commit_by_pattern('refs/tags/%', rev, True)
        if sha1 is None:
            return rev, None, self.created_date
        return self.__get_tag_changed(sha1)

    def __stat_branches_dir(self, rev):
        sha1 = self.map.get_commit_by_pattern('refs/heads/%', rev)
        return self.__get_last_changed(sha1, '', rev=rev)

    def stat(self, url, rev):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        if ref is None and path == 'tags':
            changed, by, at = self.__stat_tags_dir(rev)
            return '', 'dir', 0, changed, by, at

        if ref is None and path == 'branches':
            changed, by, at = self.__stat_branches_dir(rev)
            return '', 'dir', 0, changed, by, at

        if ref is None and path == '':
            # We have been asked about the respository root, we don't have one
            # so we have to make something up.
            sha1 = self.map.get_commit_by_rev(rev)
            changed, by, at = self.__get_last_changed(sha1, path, rev=rev)
            return '', 'dir', 0, changed, by, at

        if sha1 is None:
            return None, None, 0, 0, None, None

        if path == '':
            type = 'tree'
            size = 0

        else:
            data = self.__ls_tree(sha1, path)

            if len(data) != 1:
                return None, None, 0, 0, None, None

            mode, type, sha, size, git_path = data[0]

        kind = self.__map_type(type)

        changed, by, at = self.__get_last_changed(sha1, path, rev=rev)

        return path, kind, size, changed, by, at

    def ls(self, url, rev, include_changed=True):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        ls_data = []

        if ref is None and path == 'tags':
            tags = self.__list_tags()
            for name in tags:
                sha1 = self.map.find_commit('refs/tags/%s' % name, rev, True)
                changed, by, at = None, None, None
                if sha1 is None:
                    # lightweight tags don't have their own sha1 ...
                    sha1 = self.map.find_commit('refs/tags/%s' % name, rev)
                    if sha1 is None:
                        continue
                    if include_changed:
                        changed, by, at = self.__get_last_changed(sha1, '', rev=rev)
                else:
                    if include_changed:
                        changed, by, at = self.__get_tag_changed(sha1)
                ls_data.append((name, 'dir', 0, changed, by, at))
            return ls_data

        if ref is None and path == 'branches':
            branches = self.__list_branches()
            for name in branches:
                if name == "master":
                    continue
                sha1 = self.map.find_commit('refs/heads/%s' % name, rev)
                changed, by, at = None, None, None
                if sha1 is None:
                    continue
                if include_changed:
                    changed, by, at = self.__get_last_changed(sha1, '', rev=rev)
                ls_data.append((name, 'dir', 0, changed, by, at))
            return ls_data

        if ref is None and path == '':
            if include_changed:
                changed, by, at = self.__stat_tags_dir(rev)
            ls_data.append(('tags', 'dir', 0, changed, by, at))
            if include_changed:
                changed, by, at = self.__stat_branches_dir(rev)
            ls_data.append(('branches', 'dir', 0, changed, by, at))
            sha1 = self.map.find_commit('refs/heads/master', rev)
            changed, by, at = None, None, None
            if include_changed:
                changed, by, at = self.__get_last_changed(sha1, '', rev=rev)
            ls_data.append(('trunk', 'dir', 0, changed, by, at))
            return ls_data

        if len(path) > 0 and path[-1] != '/':
            path += '/'

        for mode, type, sha, size, name in self.__ls_tree(sha1, path):
            kind = self.__map_type(type)
            if include_changed:
                changed, by, at = self.__get_last_changed(sha1, name, rev=rev)
            else:
                changed, by, at = None, None, None
            if name.startswith(path):
                name = name[len(path):]
            if name == '.gitignore':
                continue
            if name == '.gitprops':
                continue
            ls_data.append((name, kind, size, changed, by, at))

        return ls_data

    def log(self, url, target_paths, start_rev, end_rev, limit):
        ref, path = self.__map_url(url)

        if start_rev > end_rev:
            frm = end_rev
            to = start_rev
            order = 'DESC'
        else:
            frm = start_rev
            to = end_rev
            order = 'ASC'

        commits = self.map.get_commits(ref, frm, to, order)

        print path, target_paths

        for row in commits:
            #rev, action, sha1, origin = row
            rev = row['revision']
            sha1 = row['sha1']

            changed = {}
            for p, c in self.__get_changed_paths(sha1, path).items():
                for tp in target_paths:
                    if not p.startswith(tp):
                        continue
                    kind, tmod, pmod, primary = 'file', False, False, True
                    if p == '.gitignore':
                        p, kind, pmod = '', 'dir', True
                    elif p.endswith('/.gitignore'):
                        p, kind, pmod = p[:-11], 'dir', True
                    elif p.startswith('.gitprops'):
                        primary = False
                        p, c, pmod = p[10:], 'M', True
                        if p == '.gitprops':
                            p, kind = '', 'dir'
                    elif '/.gitprops/' in p:
                        primary = False
                        pth, name = p.split('/.gitprops/')
                        p, c, pmod = '/'.join((pth, name)), 'M', True
                        if name == '.gitprops':
                            p, kind = pth, 'dir'
                    else:
                        tmod = True
                    p = '/' + p
                    prev = changed.get(p, None)
                    if prev is None:
                        changed[p] = (c, None, None, kind, tmod, pmod)
                        continue
                    tmod = tmod or prev[4]
                    pmod = pmod or prev[5]
                    if not primary:
                        c, kind = prev[0], prev[3]
                    changed[p] = (c, None, None, kind, tmod, pmod)

            if len(changed) == 0:
                continue

            has_children = False
            revprops = []
            t, p, n, author, date, msg = self.__commit_info(sha1)

            yield (changed, rev, author, date, msg, has_children, revprops)

    def rev_proplist(self, rev):
        raise NotImplemented()

    def get_props(self, url, rev, include_internal=True, mode=None):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        props = self.__load_props(sha1, path)

        if path != '':
            if mode is not None:
                data = [[mode]]
            else:
                data = self.__ls_tree(sha1, path)

            if len(data) == 1:
                mode = data[0][0]

                props.extend(self.__get_svn_props(mode))

        if not include_internal:
            return props

        changed, by, at = self.__get_last_changed(sha1, path, rev=rev)

        props.extend(self.__svn_internal_props(changed, by, at))

        return props

    def path_changed(self, url, rev, prev_rev):
        ref, path = self.__map_url(url)
        old_sha = self.map.find_commit(ref, rev)
        new_sha = self.map.find_commit(ref, prev_rev)

        return self._path_changed(old_sha, new_sha, path)

    def paths_different(self, url, rev, prev_url, prev_rev):
        ref, path = self.__map_url(url)
        prev_ref, prev_path = self.__map_url(prev_url)

        if path != prev_path:
            raise (foo)

        old_sha = self.map.find_commit(ref, rev)
        new_sha = self.map.find_commit(prev_ref, prev_rev)

        return self._path_changed(old_sha, new_sha, path)

    def get_file(self, url, rev, indep_contents=False):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        if path == '':
            return rev, [], None

        data = self.__ls_tree(sha1, path)

        if len(data) != 1:
            return rev, [], None

        mode, type, sha, size, git_path = data[0]

        if type != 'blob':
            return rev, [], None

        props = self.get_props(url, rev, mode=mode)

        return rev, props, self.__get_file_contents(mode, sha, indep_contents)

    def get_files(self, url, rev):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        # find out what files exist in the requested commit under the given path

        paths = {}
        prop_paths = {}
        for mode, type, sha, size, name in self.__ls_tree(sha1, path,
                                                          options='-r -t'):
            paths[name] = (type, mode, sha)
            prop_paths[self.__prop_path(name)] = name

        # find out when the files discovered above last changed, and who made
        # that commit

        commit, email, data = None, None, None
        changed_paths = {}
        changed_cache = {}
        for line in self.__log(sha1, path, format='/c/%H%n/a/%ae%n/d/%ad%n//',
                               options='--date=raw --name-only'):
            if line.startswith('/c/'):
                commit = line[3:]
                continue

            if line.startswith('/a/'):
                email = line[3:]
                continue

            if line.startswith('/d/'):
                when = int(line[3:-6].strip())
                tz = int(line[-5:].strip())
                tz_secs = 60 * (60 * (tz / 100) + (tz % 100))
                date = format_time(time.gmtime(when + tz_secs))
                continue

            if line.startswith('//'):
                ref, changed = self.map.get_ref_rev(commit)
                changed_cache[commit] = changed, email, date
                continue

            if line in paths and line not in changed_paths:
                changed_paths[line] = commit

            if line in prop_paths:
                name = prop_paths[line]
                if name not in changed_paths:
                    changed_paths[name] = commit

            if len(changed_paths) == len(paths):
                break

        # assemble the recursive structure for the update command

        file_data = {}

        for fpath, (type, mode, sha) in paths.items():
            if '/' in fpath:
                parent, name = fpath.rsplit('/', 1)
            else:
                parent, name = '', fpath

            if fpath not in changed_paths:
                last_commit = sha1
            else:
                last_commit = changed_paths[fpath]
            if last_commit in changed_cache:
                changed, by, at = changed_cache[last_commit]
            else:
                print "changed_cache miss"
                ref, changed = self.map.get_ref_rev(last_commit)
                t, p, n, by, at, m = self.__commit_info(last_commit)
                changed_cache[last_commit] = changed, by, at

            props = self.__load_props(last_commit, fpath)
            props.extend(self.__svn_internal_props(changed, by, at))
            contents = []

            parent_name = parent
            if '/' in parent:
                parent_name = parent.rsplit('/', 1)[-1]
            def_parent = [parent_name, 'dir', [], []]

            if name == '.gitignore':
                contents = self.__get_file_contents(mode, sha)
                prop = 'svn:ignore', contents.read()
                contents.close()
                file_data.setdefault(parent, def_parent)[2].append(prop)
                continue

            if name == '.gitprops':
                continue

            if type == 'blob':
                contents = self.__get_file_contents(mode, sha)
                props.extend(self.__get_svn_props(mode))

            if fpath in file_data:
                file_data[fpath][2].extend(props)
            else:
                kind = self.__map_type(type)
                file_data[fpath] = [name, kind, props, contents]

            file_data.setdefault(parent, def_parent)[3].append(file_data[fpath])

        return file_data[path]

    internal_props = [
        'svn:executable',
        'svn:ignore',
        'svn:special',
        'svn:entry:uuid',
        'svn:entry:committed-rev',
        'svn:entry:committed-date',
        'svn:entry:last-author',
    ]

    def __prop_path(self, filepath):
        dir, name = os.path.split(filepath)
        if name == '':
            name = '.gitprops'
        return os.path.join(dir, '.gitprops', name)

    def __load_props(self, commit, filepath):
        if filepath.startswith('.gitprops'):
            return []

        path = self.__prop_path(filepath)

        data = self.__ls_tree(commit, path)

        if len(data) != 1:
            return []

        mode, type, sha, size, git_path = data[0]

        if type != 'blob':
            return []

        contents = self.__get_file_contents(mode, sha, True)
        props = json.loads(contents.read())
        contents.close()

        return list(props.items())

    def __save_props(self, filepath, props):
        path = self.__prop_path(filepath)

        external_props = {}
        for name, value in props.items():
            if name in self.internal_props:
                continue
            external_props[name] = value

        if len(external_props) == 0:
            return '0', '0' * 40, path

        data = json.dumps(external_props)

        f = GitFile(location=self.location)
        f.write(data)
        sha1 = f.close()

        return '100644', sha1, path

    def __update_props(self, commit, filepath, propmods):
        props = {}
        done = []
        for name, value in self.__load_props(commit, filepath):
            if name not in propmods:
                props[name] = value
            elif propmods[name] is not None:
                props[name] = propmods[name]
            done.append(name)
        for name in propmods:
            if name not in done:
                props[name] = propmods[name]
        return self.__save_props(filepath, props)

    def do_commit(self, commit, msg):
        orig_index_file = os.environ.get('GIT_INDEX_FILE', '')
        orig_author = os.environ.get('GIT_AUTHOR_NAME', ''), \
                      os.environ.get('GIT_AUTHOR_EMAIL', '')
        orig_committer = os.environ.get('GIT_COMMITTER_NAME', ''), \
                         os.environ.get('GIT_COMMITTER_EMAIL', '')

        # each connection needs its own index file, so that two connection doing
        # commits simulataneously don't corrupt each other ...
        index_file = 'svnserver/%s.idx' % uuid.uuid4()
        os.environ['GIT_INDEX_FILE'] = index_file

        os.environ['GIT_AUTHOR_NAME'] = commit.user.name
        os.environ['GIT_AUTHOR_EMAIL'] = commit.user.email
        os.environ['GIT_COMMITTER_NAME'] = commit.user.name
        os.environ['GIT_COMMITTER_EMAIL'] = commit.user.email

        cmd = '--bare read-tree %s' % commit.parent
        self.__get_git_data(cmd)

        cmd = '--bare update-index --add --index-info'
        ui = GitData(self.location, cmd)

        for relpath, data in commit.dirs.items():
            path = os.path.join(commit.prefix, relpath)

            props = data.get('props', {})

            # we want to commit a .gitignore file even if the svn:ignore
            # property is empty - as we use the .gitignore file to represent the
            # directory since git won't track them directly.
            f = GitFile(location=self.location)
            f.write(props.get('svn:ignore', ''))
            sha = f.close()

            ppath = os.path.join(path, '.gitignore')
            ui.write('100644 %s\t%s\n' % (sha, ppath))

            pmode, psha, ppath = self.__update_props(commit.parent, path, props)
            ui.write('%s %s\t%s\n' % (pmode, psha, ppath))

        for relpath, data in commit.files.items():
            path = os.path.join(commit.prefix, relpath)

            if 'delete' in data:
                ui.write('%s %s\t%s\n' % ('0', '0' * 40, path))
                continue

            if 'sha1' in data:
                sha = data['sha1']
            else:
                # The file contents haven't changed, so we have to look up the
                # old sha1 for this path ...
                fdata = self.__ls_tree(commit.parent, path)
                if len(fdata) != 1:
                    print "failed to get existing sha1!"
                    continue
                m, t, sha, s, gp = fdata[0]

            props = data.get('props', {})

            pmode, psha, ppath = self.__update_props(commit.parent, path, props)
            ui.write('%s %s\t%s\n' % (pmode, psha, ppath))

            mode = '100644'

            if 'svn:special' in props:
                mode, sha = self.__translate_special(sha)
                if sha is None:
                    print 'some unknown type of svn special object has been ' \
                          'sent!'
                    continue

            if 'svn:executable' in props:
                mode = '100755'

            ui.write('%s %s\t%s\n' % (mode, sha, path))

        ui.close()

        cmd = '--bare write-tree'
        tree = self.__get_git_data(cmd)[0]

        cmd = '--bare commit-tree %s -p %s' % (tree, commit.parent)
        ct = GitData(self.location, cmd)
        ct.write(msg)
        ct.close_stdin()
        commit_sha = ct.read().strip()
        ct.close()

        cmd = 'push --porcelain . %s:%s' % (commit_sha, commit.ref)
        self.__get_git_data(cmd)

        index_file = os.path.join(self.location, index_file)
        if os.path.exists(index_file):
            os.remove(index_file)

        os.environ['GIT_INDEX_FILE'] = orig_index_file
        os.environ['GIT_AUTHOR_NAME'] = orig_author[0]
        os.environ['GIT_AUTHOR_EMAIL'] = orig_author[0]
        os.environ['GIT_COMMITTER_NAME'] = orig_committer[0]
        os.environ['GIT_COMMITTER_EMAIL'] = orig_committer[0]

        return commit_sha

    def do_tag(self, name, url, rev, msg, user):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        print "create tag %s from %s@%d" % (name, url, rev)
        print "create tag %s from %s[%s]" % (name, ref, sha1[:8])

        timestamp = time.time()
        now = time.localtime(timestamp)
        # Calculate timezone offset, based on whether the local zone has
        # daylight savings time, and whether DST is in effect.
        if time.daylight and now[-1]:
            offset = time.altzone
        else:
            offset = time.timezone
        hours, minutes = divmod(abs(offset), 3600)
        # Remember offset is in seconds west of UTC, but the timezone is in
        # minutes east of UTC, so the signs differ.
        if offset > 0:
            sign = '-'
        else:
            sign = '+'
        date = '%d %s%02d%02d' % (int(timestamp), sign, hours, minutes // 60)

        mktag = GitData(self.location, 'mktag')
        mktag.write('object %s\n' % sha1)
        mktag.write('type commit\n')
        mktag.write('tag %s\n' % name)
        mktag.write('tagger %s <%s> %s\n' % (user.name, user.email, date))
        if len(msg) > 0:
            mktag.write('\n%s\n' % msg)
        mktag.close_stdin()
        tag_sha = mktag.read().strip()
        mktag.close()

        cmd = 'push --porcelain . %s:%s' % (tag_sha, 'refs/tags/%s' % name)
        self.__get_git_data(cmd)

        print "created refs/tags/%s[%s]" % (name, tag_sha[:8])

        return tag_sha

    def do_branch(self, name, url, rev, msg, user):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        print "create branch %s from %s@%d" % (name, url, rev)
        print "create branch %s from %s[%s]" % (name, ref, sha1[:8])

        orig_index_file = os.environ.get('GIT_INDEX_FILE', '')
        orig_author = os.environ.get('GIT_AUTHOR_NAME', ''), \
                      os.environ.get('GIT_AUTHOR_EMAIL', '')
        orig_committer = os.environ.get('GIT_COMMITTER_NAME', ''), \
                         os.environ.get('GIT_COMMITTER_EMAIL', '')

        os.environ['GIT_INDEX_FILE'] = 'svnserver/tmp-index'

        os.environ['GIT_AUTHOR_NAME'] = user.name
        os.environ['GIT_AUTHOR_EMAIL'] = user.email
        os.environ['GIT_COMMITTER_NAME'] = user.uname
        os.environ['GIT_COMMITTER_EMAIL'] = user.email

        tree, p, n, e, d, m = self.__commit_info(sha1)

        cmd = '--bare commit-tree %s -p %s' % (tree, sha1)
        print cmd
        ct = GitData(self.location, cmd)
        ct.write(msg)
        ct.close_stdin()
        commit_sha = ct.read().strip()
        ct.close()

        print "create commit", commit_sha

        cmd = 'push --porcelain . %s:%s' % (commit_sha, 'refs/heads/%s' % name)
        print cmd
        print self.__get_git_data(cmd)

        os.environ['GIT_INDEX_FILE'] = orig_index_file
        os.environ['GIT_AUTHOR_NAME'] = orig_author[0]
        os.environ['GIT_AUTHOR_EMAIL'] = orig_author[0]
        os.environ['GIT_COMMITTER_NAME'] = orig_committer[0]
        os.environ['GIT_COMMITTER_EMAIL'] = orig_committer[0]

        return commit_sha

    def start_commit(self, url, user):
        """

        :type user: User
        """
        ref, path = self.__map_url(url)

        parent = None
        if ref is not None:
            try:
                cmd = '--bare rev-parse %s' % ref
                parent = self.__get_git_data(cmd)[0]
            except GitError:
                ref = None

        print 'ref: %s, path: %s, parent: %s' % (ref, path, parent)

        return GitCommit(self, url, ref, parent, path, user)

    def complete_simple_commit(self, commit, msg):
        if commit.ref.startswith('refs/tags/'):
            raise HookFailure(1, "Commits to tags are not permitted.")

        sha = self.do_commit(commit, msg)
        t, p, n, email, date, m = self.__commit_info(sha)

        ref, rev = self.map.get_ref_rev(sha)
        return rev, date, email, ""

    def complete_commit(self, commit, msg):
        """


        :type msg: str
        :type commit: GitCommit
        """
        if commit.ref is not None:
            return self.complete_simple_commit(commit, msg)

        print 'hmmm', commit.dirs, commit.files

        if len(commit.files) > 0:
            raise HookFailure(1, "General commits are only permitted to trunk, "
                                 "or an existing branch.")

        tag = None
        branch = None

        for path, data in commit.dirs.items():
            ref, path = self.__map_url("/".join((commit.url, path)))
            print "..", ref, path
            if ref is None:
                raise HookFailure(1, "Only commits to trunk, tags and branches"
                                     " are permitted.")
            if path != '':
                raise HookFailure(1, "You may not commit to a non-existant tag"
                                     " or branch.")
            url = data.get('url', None)
            rev = data.get('rev', None)
            if ref.startswith('refs/tags/'):
                if tag is not None or branch is not None:
                    raise HookFailure(1, "Only one branch or tag may be "
                                         "created per commit.")
                if url is None or rev is None:
                    raise HookFailure(1, "A tag may only be created by copying"
                                         " an existing tag or branch")
                tag = ref[10:], url, rev, msg
            elif ref.startswith('refs/heads/'):
                if tag is not None or branch is not None:
                    raise HookFailure(1, "Only one branch or tag may be "
                                         "created per commit.")
                branch = ref[11:], url, rev, msg

        if tag is not None:
            sha = self.do_tag(*tag, user=commit.user)
            o, t, tn, n, email, date, m = self.__tag_info(sha)
        elif branch is not None:
            sha = self.do_branch(*branch, user=commit.user)
            t, p, n, email, date, m = self.__commit_info(sha)

        ref, rev = self.map.get_ref_rev(sha)
        return rev, date, email, ""
