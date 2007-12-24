#! /usr/bin/env python

# Directory integrity scanner.

from stat import *
import os
import sys
from os.path import join

from cPickle import dump, load

def walk(top):
    """Root of directory generator"""
    topstat = os.lstat(top)
    for x in walker(top, '.', topstat):
	yield x

def walker(path, name, topstat):
    """Directory tree generator.

    At one point, this started as a copy of os.walk from Python's
    library.  Even the arguments are different now.
    """

    try:
	names = os.listdir(path)
    except OSError:
	sys.stderr.write("Warning, can't read dir: %s\n" % path)
	return

    # The verification algorithm requires the names to be sorted.
    names.sort()

    # Stat each name found, and put the result in one of two lists.
    dirs, nondirs = [], []
    for onename in names:
	st = os.lstat(join(path, onename))
	if S_ISDIR(st.st_mode):
	    dirs.append((onename, st))
	else:
	    nondirs.append((onename, st))

    # Indicate "entering" the directory.
    yield 'd', name

    # Then recursively walk into all of the subdirectories.
    for (onename, st) in dirs:
	subpath = join(path, onename)
	if st.st_dev == topstat.st_dev:
	    for x in walker(subpath, onename, topstat):
		yield x

    # Then yield each entry that is not a subdirectory.
    for (onename, st) in nondirs:
	yield '-', onename

    # Last, yield the leaving.
    yield ('u', name)

if __name__ == '__main__':
    "Test this"
    for info in walk('/home/davidb/wd/asure'):
	print info
