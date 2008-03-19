
import md5
import os
import re
import sys
import time

import svndiff
from config import config

commit_tree_re = re.compile(r'tree (?P<sha>[0-9a-fA-F]{40,40})')
commit_parent_re = re.compile(r'parent (?P<sha>[0-9a-fA-F]{40,40})')
commit_author_re = re.compile(r'author (?P<name>.*) <(?P<email>.*)> (?P<when>\d+) (?P<tz>\+\d{4,4})')
commit_comitter_re = re.compile(r'comitter (?P<name>.*) <(?P<email>.*)> (?P<when>\d+) (?P<tz>\+\d{4,4})')

url_re = re.compile(r'^svn://(?P<host>[^/]+)/(?P<path>.*?)\s*$')

git_binary = "git"
verbose_mode = False


class Repos:
    def __init__(self, host, base):
        self.repos_base = base
        self.uuid = 'ffffffff-ffff-ffff-ffff-ffffffffffff'
        self.base_url = 'svn://%s/%s' % (host, base)
        self.repos = config.repos[base]
        self.trunk_re = re.compile(r'^%s/%s(/(?P<path>.*))?$' % \
                                   (self.base_url, self.repos.trunk))
        branches = self.repos.branches.replace('$(branch)', '(?P<branch>[^/]+)')
        self.branch_re = re.compile(r'^%s/%s(/(?P<path>.*))?$' % \
                                    (self.base_url, branches))
        tags = self.repos.tags.replace('$(tag)', '(?P<tag>[^/]+)')
        self.tag_re = re.compile(r'^%s/%s(/(?P<path>.*))?$' % \
                                 (self.base_url, tags))
        self.other_re = re.compile(r'^%s(/(?P<path>.*))?$' % \
                                   (self.base_url))

    def send_server_id(self, link):
        link.send_msg(gen.success(gen.string(self.uuid),
                                  gen.string(self.base_url)))

    def get_git_data(self, command_string):
        git_command = "%s %s" % (git_binary, command_string)

        if verbose_mode:
            print "  >> %s" % (git_command)

        cwd = os.getcwd()
        os.chdir(self.repos.location)

        (git_in, git_data, git_err) = os.popen3(git_command)

        data = [line.strip('\n') for line in git_data]

        git_in.close()
        git_data.close()
        git_err.close()

        os.chdir(cwd)

        return data

    def get_raw_git_data(self, command_string):
        git_command = "%s %s" % (git_binary, command_string)

        if verbose_mode:
            print "  >> %s" % (git_command)

        cwd = os.getcwd()
        os.chdir(self.repos.location)

        (git_in, git_data, git_err) = os.popen3(git_command)

        data = git_data.read()

        git_in.close()
        git_data.close()
        git_err.close()

        os.chdir(cwd)

        return data

    def parse_url(self, url):
        if url == self.base_url:
            return (None, '')

        trunk_m = self.trunk_re.search(url)
        branch_m = self.branch_re.search(url)
        tag_m = self.tag_re.search(url)
        other_m = self.other_re.search(url)

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

    def get_rev_map(self):
        orig_path = sys.path
        sys.path = [self.repos.location]
        from sha_map import rev_map
        sys.path = orig_path
        return rev_map

    def map_ref(self, ref):
        orig_path = sys.path
        sys.path = [self.repos.location]
        from sha_map import sha_map
        sys.path = orig_path
        return sha_map.get(ref, None)

    def get_latest_rev(self):
        max_rev = 0

        for rev in self.get_rev_map().keys():
            max_rev = max(max_rev, rev)

        return max_rev

    def map_rev(self, ref, rev):
        ref_map = {}
        rev_map = self.get_rev_map()

        if ref in ref_map:
            revs = foo
            commit = ref_map[ref][rev]
        else:
            commit = rev_map[rev]

        return commit

    def get_path_info(self, url, rev=None, recurse=False):
        ref, path = self.parse_url(url)
        
        commit = self.map_rev(ref, rev)

        opts = ''
        if recurse:
            opts += '-r -t'

        cmd = 'ls-tree %s %s "%s"' % (opts, commit, path)

        data = self.get_git_data(cmd)

        print data

        if len(data) != 1:
            return (None, None, None)

        mode, type, sha, git_path = data[0].split()

        if path != git_path:
            return (None, None, None)

        return mode, type, sha

    def stat_pseudo_path(self, path, rev=None):

        if self.repos.trunk.startswith(path):
            pass

        if self.repos.branches.startswith(path):
            pass

        if self.repos.tags.startswith(path):
            pass

        raise foo

        return (fname, kind, int(size),
                last_changed, last_changed_by, last_changed_at)

    def stat(self, url, rev=None):
        ref, path = self.parse_url(url)

        if ref is None:
            return self.stat_pseudo_path(path, rev)

        commit = self.map_rev(ref, rev)

        if path == '':
            cmd = 'rev-parse %s^{tree}' % (commit)

            data = self.get_git_data(cmd)

            if len(data) > 1:
                raise foo

            type = 'tree'
            sha = data[0]
            name = ''
            fname = ''

        else:
            cmd = 'ls-tree -l %s "%s"' % (commit, path)

            data = self.get_git_data(cmd)

            if len(data) > 1:
                raise foo

            mode, type, sha, size, name = data[0].split()
            name_bits = name.split('/')

            fname = name_bits[-1]

        if type == 'tree':
            size = 0

        kind = self.kind_map(type)

        name_rev = self.get_git_data('rev-list -n 1 %s -- %s' % \
                                     (commit, name))
        if len(name_rev) != 1:
            last_changed = 0
            last_changed_by = '...'
        else:
            last_commit = name_rev[0]
            last_changed = self.map_ref(last_commit)
            t, p, n, email, at, m = self.get_commit_info(last_commit)
            last_changed_at = at
            last_changed_by = email

        return (fname, kind, int(size),
                last_changed, last_changed_by, last_changed_at)

    def ls(self, url, rev=None):
        ref, path = self.parse_url(url)
        if path == '':
            path_bits = []
        else:
            path_bits = path.split('/')

        commit = self.map_rev(ref, rev)

        cmd = 'ls-tree -l -r -t %s "%s"' % (commit, path)

        data = self.get_git_data(cmd)

        ls_data = []
        for line in data:
            mode, type, sha, size, name = line.split()
            name_bits = name.split('/')

            if len(name_bits) != len(path_bits) + 1:
                continue

            if '/'.join(name_bits[:-1]) != path:
                continue

            fname = name_bits[-1]

            if type == 'tree':
                size = 0

            kind = self.kind_map(type)

            name_rev = self.get_git_data('rev-list -n 1 %s -- %s' % \
                                         (commit, name))
            if len(name_rev) != 1:
                last_changed = 0
                last_changed_by = '...'
            else:
                last_commit = name_rev[0]
                last_changed = self.map_ref(last_commit)
                t, p, n, email, at, m = self.get_commit_info(last_commit)
                last_changed_at = at
                last_changed_by = email

            ls_data.append((fname, kind, int(size),
                            last_changed, last_changed_by, last_changed_at))

        return ls_data

    def get_update(self, url, rev, previous_url=None, previous_rev=None):
        pdata = []
        if previous_url is not None and previous_rev is not None:
            pref, ppath = self.parse_url(previous_url)
            pcommit = self.map_rev(pref, previous_rev)

            cmd = 'ls-tree -l -r -t %s "%s"' % (pcommit, ppath)
            pdata = self.get_git_data(cmd)

        ref, path = self.parse_url(url)
        commit = self.map_rev(ref, rev)

        cmd = 'ls-tree -l -r -t %s "%s"' % (commit, path)
        data = self.get_git_data(cmd)

        prev = {}
        for line in pdata:
            mode, type, sha, size, name = line.split()
            if type == 'tree':
                name += '/'
            prev[name] = (mode, type, sha, size)

        added = []
        modified = []
        deleted = []

        now = {}
        for line in data:
            mode, type, sha, size, name = line.split()
            if type == 'tree':
                name += '/'
            now[name] = (mode, type, sha, size)

            if name not in prev:
                added.append(name)
                continue

            pmode, ptype, psha, psize = prev[name]

            if pmode != mode or \
                   ptype != type or \
                   psha != sha or \
                   psize != size:
                modified.append(name)

        for name in prev:
            if name not in now:
                deleted.append(name)

        for name in sorted(added + modified + deleted):
            mode, type, sha, size = now[name]

            if name in added and type == 'blob':
                cmd = 'cat-file blob %s' % sha
                data = self.get_raw_git_data(cmd)
                diff = svndiff.encode_new_file(data)
                csum = md5.new(data).hexdigest()
                props = {}
                props['svn:entry:uuid'] = self.uuid
                yield name, self.kind_map(type), sha, props, diff, csum
                continue

            yield name, self.kind_map(type), sha, {}, [''], ''

    def get_commit_info(self, commit):
        data = self.get_git_data('cat-file commit %s' % commit)

        parents = []
        msg_offset = 0
        for line in data:
            msg_offset += 1
            if line == '':
                break
            tree_m = commit_tree_re.match(line)
            parent_m = commit_parent_re.match(line)
            author_m = commit_author_re.match(line)
            comitter_m = commit_comitter_re.match(line)
            if tree_m:
                tree = tree_m.group('sha')
            elif parent_m:
                parents.append(parent_m.group('sha'))
            elif author_m:
                name = author_m.group('name')
                email = author_m.group('email')
                when = int(author_m.group('when'))
                tz = int(author_m.group('tz'),10)

        msg = '\n'.join(data[msg_offset:])

        tz_secs = 60 * (60 * (tz/100) + (tz%100))

        date = time.strftime('%Y-%m-%dT%H:%M:%S.000000Z',
                             time.gmtime(when + tz_secs))

        return (tree, parents, name, email, date, msg)

    def kind_map(self, type):
        if type is None:
            return 'none'

        if type == 'blob':
            return 'file'

        if type == 'tree':
            return 'dir'

    def svn_node_kind(self, url, rev=None):
        mode, type, sha = self.get_path_info(url, rev)

        return self.kind_map(type)

repos_list = {}

def get_repos(host, base):
    if base in repos_list:
         return repos_list[base]
    else:
         r = Repos(host, base)
         repos_list[base] = r
         return r

def find_repos(url):
    url_m = url_re.match(url)

    if url_m is None:
        return None

    host = url_m.group('host')
    path = url_m.group('path')

    for base, repos in config.repos.items():
        if path.startswith(base):
            return get_repos(host, base)

    return None
