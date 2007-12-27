#! /usr/bin/env python

# Directory integrity scanner.

from stat import *
import os
import sys
from os.path import join

from cPickle import dump, load
import gzip

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
    yield ('u',)

version = 'Asure scan version 1.0'

def reader(path):
    """Iterate over a previously written dump"""
    fd = gzip.open(path, 'rb')
    vers = load(fd)
    if version != vers:
	raise "incompatible version of asure file"
    try:
	while True:
	    yield load(fd)
    except EOFError:
	return

def writer(path, tmppath, iter):
    """Write the given item (probably assembled iterator)"""
    fd = gzip.open(tmppath, 'wb')
    dump(version, fd, -1)
    for item in iter:
	dump(item, fd, -1)
    fd.close
    os.rename(tmppath, path)

def fresh_scan():
    """Perform a fresh scan of the filesystem"""
    writer('asure.dat.gz', 'asure.0.gz', walk('.'))

def main(argv):
    if len(argv) != 1:
	usage()
    if argv[0] == 'scan':
	fresh_scan()
    elif argv[0] == 'update':
	print "Update"
    elif argv[0] == 'check':
	print "Check"
    elif argv[0] == 'show':
	for i in reader('asure.dat.gz'):
	    print i

def usage():
    print "Usage: asure {scan|update|check}"
    sys.exit(1)

if __name__ == '__main__':
    "Test this"
    main(sys.argv[1:])
    #for info in walk('/home/davidb/wd/asure'):
    #print info
