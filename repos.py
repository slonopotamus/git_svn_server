
import os
import re

from config import config

url_re = re.compile(r'^svn://(?P<host>[^/]+)/(?P<path>.*?)\s*$')

git_binary = "git"
verbose_mode = False


class Repos:
    def __init__(self, host, base):
        self.repos_base = base
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

    def parse_url(self, url):
        if url == self.base_url:
            return (None, '')

        trunk_m = self.trunk_re.search(url)
        branch_m = self.branch_re.search(url)
        tag_m = self.tag_re.search(url)

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
        else:
            raise foo

        if path == None:
            path = ''

        return (ref, path)

    def map_rev(self, ref, rev):
        return ref

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

    def svn_node_kind(self, url, rev=None):
        mode, type, sha = self.get_path_info(url, rev)

        if type is None:
            return 'none'

        if type == 'blob':
            return 'file'

        if type == 'tree':
            return 'dir'

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
