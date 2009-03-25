
import os
import re
import sqlite3

from GitSvnServer import repos


git_binary = "git"


class GitData (object):
    def __init__(self, command_string):
        self._cmd = "%s %s" % (git_binary, command_string)
        self.open()

    def open(self):
        if verbose_mode:
            print "  >> %s" % (self._cmd)

        (self._in, self._data, self._err) = os.popen3(self._cmd)

    def read(self, l=-1):
        return self._data.read(l)

    def close(self):
        self._in.close()
        self._data.close()
        self._err.close()

    def reopen(self):
        self.close()
        self.open()


class GitMap (object):
    def __init__(self, repo_location):
        self.map_file = os.path.join(repo_location, 'svnserver', 'map')

    def __connect(self):
        conn = sqlite3.connect(self.map_file)
        conn.row_factory = sqlite3.Row
        return conn

    def __execute(self, sql, *args):
        conn = self.__connect()
        results = conn.execute(sql, args).fetchall()
        conn.close()
        return results

    def get_uuid(self):
        rows = self.__execute('SELECT value FROM meta WHERE name = "uuid"')
        if len(rows) == 0:
            return None
        return rows[0]['value']

    def get_latest_rev(self):
        conn = self.__connect()
        sql = 'SELECT revision FROM transactions ORDER BY revision DESC'
        row = conn.execute(sql).fetchone()
        conn.close()
        if row is None:
            return None
        return int(row['revision'])

    def find_commit(self, ref, rev):
        conn = self.__connect()
        sql = 'SELECT revision, action, sha1 FROM transactions WHERE ref = ? ' \
              'AND revision <= ? ORDER BY revision DESC'
        row = conn.execute(sql, (ref, rev)).fetchone()
        conn.close()

        if row is None:
            return None

        if row['action'] in ['commit', 'create branch']:
            return rows[i]['sha1']
        elif row['action'] == 'delete branch':
            return None

        return None


class Git (repos.Repos):
    _kind = 'git'

    def __init__(self, host, base, config):
        super(Git, self).__init__(host, base, config)
        self.map = GitMap(config.location)
        self.trunk_re = re.compile(r'^%s/%s(/(?P<path>.*))?$' %
                                   (self.base_url, config.trunk))
        branches = config.branches.replace('$(branch)', '(?P<branch>[^/]+)')
        self.branch_re = re.compile(r'^%s/%s(/(?P<path>.*))?$' %
                                    (self.base_url, branches))
        tags = config.tags.replace('$(tag)', '(?P<tag>[^/]+)')
        self.tag_re = re.compile(r'^%s/%s(/(?P<path>.*))?$' %
                                 (self.base_url, tags))
        self.other_re = re.compile(r'^%s(/(?P<path>.*))?$' %
                                   (self.base_url))

    def __get_git_data(self, command_string):
        git_data = GitData(command_string)

        data = [line.strip('\n') for line in git_data._data]

        git_data.close()

        return data

    def __map_url(url):
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

    def __map_type(self, type):
        if type is None:
            return 'none'

        if type == 'blob':
            return 'file'

        if type == 'tree':
            return 'dir'

    def _calc_uuid(self):
        self.uuid = self.map.get_uuid()

    def get_latest_rev(self):
        return self.map.get_latest_rev()

    def __ls_tree(self, sha1, path, options=''):
        results = []

        cmd = 'ls-tree %s "%s"' % (sha1, path)

        for mode, type, sha, git_path in self.__get_git_data(cmd):
            results.append((mode, type, sha, git_path))

        return results

    def check_path(self, url, rev):
        ref, path = self.__map_url(url)
        sha1 = self.map.find_commit(ref, rev)

        if sha1 is None:
            return 'none'

        data = self.__ls_tree(sha1, path)

        if len(data) != 1:
            return 'none'

        return self.__map_type(data[0][1])

    def stat(self, url, rev):
        raise repos.UnImplemented

    def ls(self, url, rev):
        raise repos.UnImplemented

    def log(self, url, target_paths, start_rev, end_rev, limit):
        raise repos.UnImplemented

    def rev_proplist(self, rev):
        raise repos.UnImplemented

    def get_props(self, url, rev, include_internal=True):
        raise repos.UnImplemented

    def get_file(self, url, rev):
        raise repos.UnImplemented
