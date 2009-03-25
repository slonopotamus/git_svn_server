
import os

from GitSvnServer import repos

import xml.etree.cElementTree as ElementTree


svn_binary = "svn"
verbose_mode = False

svn_internal_props = ['svn:entry:uuid',
                      'svn:entry:last-author',
                      'svn:entry:committed-rev',
                      'svn:entry:committed-date']


class SvnData (object):
    def __init__(self, command_string):
        self._cmd = "%s %s" % (svn_binary, command_string)
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


class Svn (repos.Repos):
    _kind = 'svn'

    def __init__(self, host, base, config):
        super(Svn, self).__init__(host, base, config)

    def __get_svn_data(self, command_string):
        svn_data = SvnData(command_string)

        data = [line.strip('\n') for line in svn_data._data]

        svn_data.close()

        return data

    def __get_svn_xml(self, command_string):
        svn_data = SvnData("--xml %s" % command_string)

        element = ElementTree.parse(svn_data._data)

        svn_data.close()

        return element.getroot()

    def __get_svn_props(self, command_string):
        data = self.__get_svn_data(command_string)

        props = []
        for line in data:
            if line.startswith('  '):
                name, value = line[2:].split(' : ', 1)
                props.append((name, value))
            elif len(props) > 0:
                name, value = props[-1]
                value += '\n' + line
                props[-1] = (name, value)

        return props

    def __map_url(self, url, rev=None):
        new_url = url

        if url.startswith(self.base_url):
            new_url = url.replace(self.base_url, self.config.location)

        if rev is not None:
            new_url = "%s@%d" % (new_url, rev)

        return new_url

    def _calc_uuid(self):
        data = self.__get_svn_data('info %s' % self.config.location)

        for line in data:
            if line.startswith('Repository UUID:'):
                self.uuid = line[17:]
                return

    def get_latest_rev(self):
        latest_rev = None

        data = self.__get_svn_data('info %s' % self.config.location)

        for line in data:
            if line.startswith('Revision:'):
                latest_rev = int(line[10:])
                break

        return latest_rev

    def check_path(self, url, rev):
        location = self.__map_url(url, rev)

        xml = self.__get_svn_xml('info %s' % location)

        if len(xml) == 0:
            return 'none'

        return xml[0].get('kind')

    def stat(self, url, rev):
        path, kind, size, changed, by, at = None, None, 0, 0, None, None

        location = self.__map_url(url, rev)

        xml = self.__get_svn_xml('info %s' % location)

        if len(xml) == 0:
            return path, kind, size, changed, by, at

        element = xml[0]

        path = element.get('path')
        kind = element.get('kind')
        changed = int(element.find('commit').get('revision'))
        by = element.find('commit/author').text
        at = element.find('commit/date').text

        if kind == 'file':
            data = self.__get_svn_data('ls --xml %s' % location)

            for line in data:
                if line.startswith('<size>'):
                    size = int(line[6:-7])

        return path, kind, size, changed, by, at

    def ls(self, url, rev):
        location = self.__map_url(url, rev)

        ls_data = []

        xml = self.__get_svn_xml('ls %s' % location)

        if len(xml) == 0:
            return ls_data

        for element in xml[0]:
            path = element.find('name').text
            kind = element.get('kind')
            changed = int(element.find('commit').get('revision'))
            by = element.find('commit/author').text
            at = element.find('commit/date').text
            size = 0
            if kind == 'file':
                size = int(element.find('size').text)

            ls_data.append((path, kind, size, changed, by, at))

        return ls_data

    def log(self, url, target_paths, start_rev, end_rev, limit):
        location = self.__map_url(url, start_rev)

        log_data = []

        options = ['-v']

        print "target paths:", target_paths

        if limit > 0:
            options.append('--limit %d' % limit)

        options.append('-r %d:%d' % (start_rev, end_rev))
        options.append(location)

        cmd = 'log  %s' % (' '.join(options))

        xml = self.__get_svn_xml(cmd)

        for element in xml:
            changes = []
            for el in element.findall('paths/path'):
                change = el.get('action')
                path = el.text
                copy_path = el.get('copyfrom-path', None)
                copy_rev = el.get('copyfrom-rev', None)
                changes.append((path, change, copy_path, copy_rev))
            rev = int(element.get('revision'))
            author = element.find('author').text
            date = element.find('date').text
            msg = element.find('msg').text
            if msg is None:
                msg = ''
            has_children = False
            revprops = []
            log_data.append((changes, rev, author, date, msg,
                             has_children, revprops))

        return log_data

    def rev_proplist(self, rev):
        location = self.__map_url(self.base_url)

        cmd = 'proplist --revprop -v -r %d %s' % (rev, location)

        return self.__get_svn_props(cmd)

    def get_props(self, url, rev, include_internal=True):
        location = self.__map_url(url, rev)

        cmd = 'proplist -v %s' % location

        props = self.__get_svn_props(cmd)

        if not include_internal:
            return props

        for prop in svn_internal_props:
            cmd = 'propget "%s" "%s"' % (prop, location)
            value = '\n'.join(self.__get_svn_data(cmd))
            if len(value) > 0:
                props.append((prop, value))

        return props

    def get_file(self, url, rev):
        location = self.__map_url(url, rev)

        xml = self.__get_svn_xml('info %s' % location)

        if len(xml) == 0:
            return rev, [], None

        props = self.get_props(url, rev)

        cmd = 'cat %s' % location
        contents = SvnData(cmd)

        return rev, props, contents
