#!/usr/bin/python
"""Basic Functionality Tests
"""

import socket

from CleverSheep.Test.Tester import *

from lib import TestSuite

class SimpleTest (TestSuite):
    """Basic test that git-svnserver actually runs"""

    @test
    def check_runs(self):
        """Check that the server actually runs"""
        self.start_server('../test.cfg')

        s = socket.socket()
        error = s.connect_ex((self.ip, self.port))
        failUnlessEqual(0, error)


if __name__ == "__main__":
    runModule()
