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

def compare_trees(prior, cur):
    """Compare two scanned trees."""
    a = prior.next()
    if a[0] != 'd':
	raise "Scan doesn't start with a directory"
    b = cur.next()
    if b[0] != 'd':
	raise "Tree walk doesn't start with a directory"

    # We don't concern ourselves with whether the names are the same
    # at this point.
    comp_walk(prior, cur)

def comp_walk(prior, cur, depth=1):
    """Inside directory.

    Recursively walks both the "prior" and "cur" directories,
    comparing the trees found inside.  Returns when each has left this
    directory."""

    a = prior.next()
    b = cur.next()
    while True:

	# print "Comparing (%d) %s and %s" % (depth, a, b)

	# Both are 'leave' nodes.
	if a[0] == 'u' and b[0] == 'u':
	    # print "...leave"
	    return

	if a[0] == 'd' and b[0] == 'd':
	    # Both are looking at a child subdirectory.

	    if a[1] == b[1]:
		# Same name, just walk this tree.
		# print "...same dir, enter"
		comp_walk(prior, cur, depth+1)
		a = prior.next()
		b = cur.next()
		continue

	    elif a[1] < b[1]:
		# A directory has been deleted.
		print "Delete dir: %s" % a[1]
		consume_dir(prior)
		a = prior.next()
		continue

	    else:
		# A directory has been added.
		print "Add dir: %s" % b[1]
		consume_dir(cur)
		b = cur.next()
		continue

	elif a[0] == '-' and b[0] == '-':
	    # Both are looking at a non-dir.
	    if a[1] == b[1]:
		# Same name, all is well.
		# print "...same file"
		a = prior.next()
		b = cur.next()
		continue

	    elif a[1] < b[1]:
		print "Delete nondir: %s" % a[1]
		a = prior.next()
		continue

	    else:
		print "Add nondir: %s" % b[1]
		b = cur.next()
		continue

	elif a[0] == '-' and b[0] == 'u':
	    print "Delete nondir: %s" % a[1]
	    a = prior.next()
	    continue

	elif a[0] == 'u' and b[0] == '-':
	    print "New nondir: %s" % b[1]
	    b = cur.next()
	    continue

	elif a[0] == 'd' and b[0] == '-':
	    print "Delete dir: %s" % a[1]
	    consume_dir(prior)
	    a = prior.next()
	    continue

	elif (a[0] == '-' or a[0] == 'u') and b[0] == 'd':
	    print "Add dir: %s" % b[1]
	    consume_dir(cur)
	    b = cur.next()
	    continue

	else:
	    print "Unhandled case: prior: %s, cur: %s" % (a[0], b[0])
	    sys.exit(2)

def consume_dir(iter):
    """Consume entries until this directory has been exhausted"""
    while True:
	a = iter.next()
	if a[0] == 'u':
	    return
	elif a[0] == 'd':
	    consume_dir(iter)

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

def check_scan():
    """Perform a scan of the filesystem, and compare it with the scan
    file.  reports differences."""
    prior = reader('asure.dat.gz')
    cur = walk('.')
    compare_trees(prior, cur)

def main(argv):
    if len(argv) != 1:
	usage()
    if argv[0] == 'scan':
	fresh_scan()
    elif argv[0] == 'update':
	print "Update"
    elif argv[0] == 'check':
	check_scan()
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
