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
	if path == '.' and (onename == "0sure.dat.gz" or
		onename == "0sure.bak.gz" or
		onename == "0sure.0.gz"):
	    continue
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

def empty_generator():
    return
    yield ()

class comparer:
    """Class for comparing two directory iterations.  Keeps track of
    state, and allows child classes to define handlers for the various
    types of differences found."""

    def __init__(self, left, right):
	self.__left = left
	self.__right = right

    # Default handlers for the 6 possible changes (or not changes)
    # that can happen in a directory.  The adds and deletes take an
    # additional argument that will be set to true if this added or
    # remoted entity is contained in an entirely new directory.  Some
    # handlers may want to avoid printing verbose messages for the
    # contents of added or deleted directories, and can use this
    # value.
    def handle_same_dir(self, path, a, b):
	#print "same_dir(%s, %s, %s)" % (path, a, b)
	return empty_generator()
    def handle_delete_dir(self, path, a, recursing):
	#print "delete_dir(%s, %s, %s)" % (path, a, recursing)
	return empty_generator()
    def handle_add_dir(self, path, a, recursing):
	#print "add_dir(%s, %s, %s)" % (path, a, recursing)
	return empty_generator()
    def handle_same_nondir(self, path, a, b):
	#print "same_nondir(%s, %s, %s)" % (path, a, b)
	return empty_generator()
    def handle_delete_nondir(self, path, a, recursing):
	#print "delete_nondir(%s, %s, %s)" % (path, a, recursing)
	return empty_generator()
    def handle_add_nondir(self, path, a, recursing):
	#print "add_nondir(%s, %s, %s)" % (path, a, recursing)
	return empty_generator()

    def run(self):
	a = self.__left.next()
	if a[0] != 'd':
	    raise "Scan doesn't start with a directory"
	b = self.__right.next()
	if b[0] != 'd':
	    raise "Tree walk doesn't start with a directory"
	return self.__run(b[1], 1)

    def __run(self, path, depth):
	"""Iterate both pairs of directories equally

	Processes the contents of a single directory, recursively
	calling itself to handle child directories.  Returns with both
	iterators advanced past the 'u' node that ends the dir."""
	# print "run(%d): '%s'" % (depth, path)
	a = self.__left.next()
	b = self.__right.next()

	while True:
	    # print "Comparing (%d) %s and %s" % (depth, a, b)
	    if a[0] == 'u' and b[0] == 'u':
		# Both are leaving the directory.
		# print "leave(%d): '%s'" % (depth, path)
		return

	    elif a[0] == 'd' and b[0] == 'd':
		# Both looking at a directory entry.

		if a[1] == b[1]:
		    # if the name is the same, walk the tree.
		    for x in self.handle_same_dir(path, a, b):
			yield x
		    for x in self.__run(os.path.join(path, a[1]), depth + 1):
			yield x
		    a = self.__left.next()
		    b = self.__right.next()
		    continue

		elif a[1] < b[1]:
		    # A directory has been deleted.
		    for x in self.handle_delete_dir(path, a, False):
			yield x
		    for x in self.delete_whole_dir(self.__left):
			yield x
		    a = self.__left.next()
		    continue

		else:
		    # A directory has been added.
		    for x in self.handle_add_dir(path, b, False):
			yield x

		    for x in self.add_whole_dir(self.__right, path):
			yield x
		    b = self.__right.next()
		    continue

	    elif a[0] == '-' and b[0] == '-':
		# Both are looking at a non-dir.

		if a[1] == b[1]:
		    # Same name as well.
		    for x in self.handle_same_nondir(path, a, b):
			yield x
		    a = self.__left.next()
		    b = self.__right.next()
		    continue

		elif a[1] < b[1]:
		    # Deleted non-dir.
		    for x in self.handle_delete_nondir(path, a, False):
			yield x
		    a = self.__left.next()
		    continue

		else:
		    # Added non-dir.
		    for x in self.handle_add_nondir(path, b, False):
			yield x
		    b = self.__right.next()
		    continue

	    elif a[0] == '-' and b[0] == 'u':
		for x in self.handle_delete_nondir(path, a, False):
		    yield x
		a = self.__left.next()
		continue

	    elif a[0] == 'u' and b[0] == '-':
		for x in self.handle_add_nondir(path, b, False):
		    yield x
		b = self.__right.next()
		continue

	    elif a[0] == 'd' and b[0] == '-':
		for x in self.handle_delete_dir(path, a, False):
		    yield x
		for x in self.delete_whole_dir(self.__left, path):
		    yield x
		a = self.__left.next()
		continue

	    elif (a[0] == '-' or a[0] == 'u') and b[0] == 'd':
		for x in self.handle_add_dir(path, b, False):
		    yield x
		for x in self.add_whole_dir(self.__right, path):
		    yield x
		b = self.__right.next()
		continue

	    else:
		print "Unhandled case!!!"
		sys.exit(2)

    def add_whole_dir(self, iter, path):
	"Consume entries until this directory has been added"
	# print "add_whole_dir: %s" % path
	while True:
	    a = iter.next()
	    if a[0] == 'u':
		return
	    elif a[0] == 'd':
		for x in self.handle_add_dir(path, a, True):
		    yield x
		for x in self.add_whole_dir(iter, os.path.join(path, a[1])):
		    yield x
	    else:
		for x in self.handle_add_nondir(path, a, True):
		    yield x

    def delete_whole_dir(self, iter, path):
	"Consume entries until this directory has been deleted"
	# print "delete_whole_dir: %s" % path
	while True:
	    a = iter.next()
	    if a[0] == 'u':
		return
	    elif a[0] == 'd':
		for x in self.handle_delete_dir(path, a, True):
		    yield x
		for x in self.delete_whole_dir(iter, os.path.join(path, a[1])):
		    yield x
	    else:
		for x in self.handle_delete_nondir(path, a, True):
		    yield x

class check_comparer(comparer):
    """Comparer for comparing either two trees, or a tree and a
    filesystem.  'right' should be the newer tree.
    Yields strings giving the tree differences.
    """
    def handle_same_dir(self, path, a, b):
	#print "same_dir(%s, %s, %s)" % (path, a, b)
	return empty_generator()
    def handle_delete_dir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "- dir  %s" % (os.path.join(path, a[1]))
    def handle_add_dir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "+ dir  %s" % (os.path.join(path, a[1]))
    def handle_same_nondir(self, path, a, b):
	#print "same_nondir(%s, %s, %s)" % (path, a, b)
	return empty_generator()
    def handle_delete_nondir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "-      %s" % (os.path.join(path, a[1]))
    def handle_add_nondir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "+      %s" % (os.path.join(path, a[1]))

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
    writer('0sure.dat.gz', '0sure.0.gz', walk('.'))

def check_scan():
    """Perform a scan of the filesystem, and compare it with the scan
    file.  reports differences."""
    prior = reader('0sure.dat.gz')
    cur = walk('.')
    # compare_trees(prior, cur)
    for x in check_comparer(prior, cur).run():
	print x

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
	for i in reader('0sure.dat.gz'):
	    print i

def usage():
    print "Usage: asure {scan|update|check}"
    sys.exit(1)

if __name__ == '__main__':
    "Test this"
    main(sys.argv[1:])
