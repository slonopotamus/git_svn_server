#!/usr/bin/python
"""Basic Functionality Tests
"""

from CleverSheep.Test.Tester import *

from lib import TestSuite

class SimpleTest (TestSuite):
    """Basic test of git-svnserver functionality"""

    @test
    def check_runs(self):
        """Check that the server actually runs"""
        s, error = self.connect_to_server()
        failIfEqual(0, error)

        self.start_server()

        s, error = self.connect_to_server()
        failUnlessEqual(0, error)

    @test
    def check_ip(self):
        """Check that the server runs on the IP we specify"""
        orig_ip = self.ip
        self.ip = '127.1.1.1'

        s, error = self.connect_to_server()
        failIfEqual(0, error)

        self.start_server()

        s, error = self.connect_to_server(ip=orig_ip)
        failIfEqual(0, error)

        s, error = self.connect_to_server()
        failUnlessEqual(0, error)

    @test
    def check_port(self):
        """Check that the server runs on the port we specify"""
        orig_port = self.port
        self.port = 30000

        s, error = self.connect_to_server()
        failIfEqual(0, error)

        self.start_server()

        s, error = self.connect_to_server(port=orig_port)
        failIfEqual(0, error)

        s, error = self.connect_to_server()
        failUnlessEqual(0, error)

    @test
    def check_svn_info(self):
        """Check that the server looks like a Subversion server"""

        self.start_server()

        url = self.get_svn_url()
        xml = self.get_svn_xml('info %s' % url)

        failIfEqual(0, len(xml), msg='Missing entry from info')
        failIfEqual(None, xml[0].find('url'), msg='No URL in entry')
        failUnlessEqual(url, xml[0].find('url').text)


if __name__ == "__main__":
    runModule()
