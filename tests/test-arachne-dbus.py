#!/usr/bin/python

import os
import unittest

import dbus

class TestArachneDbus(unittest.TestCase):
    def setUp(self):
        self._bus = dbus.SessionBus()
        self._arachne = self._bus.get_object("at.nieslony.Arachne", "/UserVpn", True)

    def test_RunningAsUser(self):
        print("RunningAsUser")
        username = self._arachne.RunningAsUser(dbus_interface="at.nieslony.Arachne.Server")
        self.assertEqual(username, os.getlogin())

    def test_RestartServer(self):
        self._arachne.Restart()

if __name__ == '__main__':
    unittest.main()
