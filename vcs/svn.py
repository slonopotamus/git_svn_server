
import os
import repos

import xml.etree.cElementTree as ElementTree


svn_binary = "svn"
verbose_mode = False


class Svn (repos.Repos):
    _kind = 'svn'

    def __init__(self, host, base, config):
        super(Svn, self).__init__(host, base, config)

    def __get_svn_raw_data(self, command_string):
        svn_command = "%s %s" % (svn_binary, command_string)

        if verbose_mode:
            print "  >> %s" % (svn_command)

        (svn_in, svn_data, svn_err) = os.popen3(svn_command)

        data = [line.strip('\n') for line in svn_data]

        svn_in.close()
        svn_data.close()
        svn_err.close()

        return data

    def __get_svn_data(self, command_string):
        data = self.__get_svn_raw_data(command_string)

        return [line.strip('\n') for line in data]

    def __get_svn_xml(self, command_string):
        svn_command = "%s --xml %s" % (svn_binary, command_string)

        if verbose_mode:
            print "  >> %s" % (svn_command)

        (svn_in, svn_data, svn_err) = os.popen3(svn_command)

        element = ElementTree.parse(svn_data)

        svn_in.close()
        svn_data.close()
        svn_err.close()

        return element.getroot()

    def __map_url(self, url, rev=None):
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
        latest_rev = 0

        data = self.__get_svn_data('info %s' % self.config.location)

        for line in data:
            if line.startswith('Revision:'):
                latest_rev = int(line[10:])
                break

        return latest_rev

    def stat(self, url, rev):
        path, kind, size, changed, by, at = None, None, 0, 0, None, None

        location = self.__map_url(url, rev)

        xml = self.__get_svn_xml('info %s' % location)

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
