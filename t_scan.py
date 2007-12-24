#! /usr/bin/env python

from stat import *
import unittest
import asure
import os

def rm_r(path):
    try:
	st = os.lstat(path)
    except OSError:
	return
    if S_ISDIR(st.st_mode):
	for child in os.listdir(path):
	    rm_r(os.path.join(path, child))
	os.rmdir(path)
    else:
	os.unlink(path)

def touch(path):
    if os.path.lexists(path):
	raise ("Name already exists: %s" % path)
    fd = open(path, 'w')
    fd.close()

# Test Asure's directory scanning code.
class ScanUnitTest(unittest.TestCase):
    def setUp(self):
	rm_r("_test")
	os.mkdir("_test")

    def tearDown(self):
	rm_r("_test")

    def test_empty(self):
	children = [x for x in asure.walk("_test")]
	self.assertEqual(children, [('d', '.'), ('u', '.')])

    def test_single(self):
	touch("_test/aaaaa")
	self.assertEqual([x for x in asure.walk("_test")],
		[('d', '.'),
		    ('-', 'aaaaa'),
		    ('u', '.')])

    def test_subdirs(self):
	os.mkdir("_test/dir")
	os.mkdir("_test/zdir")
	touch("_test/aaa")
	touch("_test/eee")
	touch("_test/dir/aa")
	children = [x for x in asure.walk("_test")]
	self.assertEqual(children,
		[('d', '.'),
		    ('d', 'dir'),
		    ('-', 'aa'),
		    ('u', 'dir'),
		    ('d', 'zdir'),
		    ('u', 'zdir'),
		    ('-', 'aaa'),
		    ('-', 'eee'),
		    ('u', '.')])

if __name__ == '__main__':
    unittest.main()
