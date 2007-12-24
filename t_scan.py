#! /usr/bin/env python

import unittest
import asure

# Test Asure's directory scanning code.
class ScanUnitTest(unittest.TestCase):
    def setUp(self):
	print "Setup"
    def tearDown(self):
	print "TearDown"

    def testHello(self):
	print "Hello world"
    def testGoodbye(self):
	print "Goodbye"

if __name__ == '__main__':
    unittest.main()
