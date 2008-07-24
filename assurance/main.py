#! /usr/bin/env python

# Directory integrity scanner.

import math
from stat import *
import os
import sys
from os.path import join

from cPickle import dump, load
import gzip

import hashing
import version

def walk(top):
    """Root of directory generator"""
    topstat = os.lstat(top)
    for x in walker(top, '.', topstat):
	yield x

def walker(path, name, dirstat):
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
    yield 'd', name, convert_stat(dirstat)

    # Then recursively walk into all of the subdirectories.
    for (onename, st) in dirs:
	subpath = join(path, onename)
	if st.st_dev == dirstat.st_dev:
	    for x in walker(subpath, onename, st):
		yield x

    # Then yield each entry that is not a subdirectory.
    for (onename, st) in nondirs:
	yield '-', onename, convert_stat(st)

    # Last, yield the leaving.
    yield ('u',)

# Convert the passed stat info into an association of the information
# itself.  Does not do anything that requires reading the file (such
# as readlink or md5).
def convert_stat(st):
    if S_ISDIR(st.st_mode):
	return { 'kind': 'dir',
		 'uid': st.st_uid,
		 'gid': st.st_gid,
		 'perm': S_IMODE(st.st_mode) }

    elif S_ISREG(st.st_mode):
	return { 'kind': 'file',
		 'uid': st.st_uid,
		 'gid': st.st_gid,
		 'mtime': st.st_mtime,
		 'ctime': st.st_ctime,
		 'ino': st.st_ino,
		 'perm': S_IMODE(st.st_mode) }

    elif S_ISLNK(st.st_mode):
	return { 'kind': 'lnk' }

    elif S_ISSOCK:
	return { 'kind': 'sock',
		 'uid': st.st_uid,
		 'gid': st.st_gid,
		 'perm': S_IMODE(st.st_mode) }

    elif S_ISFIFO:
	return { 'kind': 'fifo',
		 'uid': st.st_uid,
		 'gid': st.st_gid,
		 'perm': S_IMODE(st.st_mode) }

    elif S_ISBLK:
	return { 'kind': 'blk',
		 'uid': st.st_uid,
		 'gid': st.st_gid,
		 'devmaj': os.major(st.st_rdev),
		 'devmin': os.minor(st.st_rdev),
		 'perm': S_IMODE(st.st_mode) }

    elif S_ISCHR:
	return { 'kind': 'chr',
		 'uid': st.st_uid,
		 'gid': st.st_gid,
		 'devmaj': os.major(st.st_rdev),
		 'devmin': os.minor(st.st_rdev),
		 'perm': S_IMODE(st.st_mode) }

    else:
	raise "Unknown file kind"

def empty_tree():
    """Make an empty tree.  No meaningful attributes for the root
    directory"""
    yield 'd', '.', {}
    yield 'u',
    return

def empty_generator():
    return
    yield ()

mode_add, mode_delete, mode_both = (1, 2, 3)

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
    def handle_leave(self, path, mode):
	"""Handle the leaving of a directory.  Instead of 'recursing',
	the mode is defined as 'mode_add' (1) for add, 'mode_delete'
	(2) for delete, or these two or'd together 'mode_both' (3) for
	both"""
	return empty_generator()

    def run(self):
	a = self.__left.next()
	if a[0] != 'd':
	    raise "Scan doesn't start with a directory"
	b = self.__right.next()
	if b[0] != 'd':
	    raise "Tree walk doesn't start with a directory"
	for x in self.handle_same_dir(".", a, b):
	    yield x
	for x in self.__run(b[1], 1):
	    yield x

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
		for x in self.handle_leave(path, mode_both):
		    yield x
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
		    for x in self.delete_whole_dir(self.__left,
			    os.path.join(path, a[1])):
			yield x
		    a = self.__left.next()
		    continue

		else:
		    # A directory has been added.
		    for x in self.handle_add_dir(path, b, False):
			yield x

		    for x in self.add_whole_dir(self.__right,
			    os.path.join(path, b[1])):
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

	    elif a[0] == 'd' and (b[0] == '-' or b[0] == 'u'):
		for x in self.handle_delete_dir(path, a, False):
		    yield x
		for x in self.delete_whole_dir(self.__left,
			os.path.join(path, a[1])):
		    yield x
		a = self.__left.next()
		continue

	    elif (a[0] == '-' or a[0] == 'u') and b[0] == 'd':
		for x in self.handle_add_dir(path, b, False):
		    yield x
		for x in self.add_whole_dir(self.__right,
		    os.path.join(path, b[1])):
		    yield x
		b = self.__right.next()
		continue

	    else:
		print "Unhandled case: '%s' and '%s'" % (a[0], b[0])
		sys.exit(2)

    def add_whole_dir(self, iter, path):
	"Consume entries until this directory has been added"
	# print "add_whole_dir: %s" % path
	while True:
	    a = iter.next()
	    if a[0] == 'u':
		for x in self.handle_leave(path, mode_add):
		    yield x
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
		for x in self.handle_leave(path, mode_delete):
		    yield x
		return
	    elif a[0] == 'd':
		for x in self.handle_delete_dir(path, a, True):
		    yield x
		for x in self.delete_whole_dir(iter, os.path.join(path, a[1])):
		    yield x
	    else:
		for x in self.handle_delete_nondir(path, a, True):
		    yield x

__must_match = {
	'dir': ['uid', 'gid', 'perm'],
	'file': ['uid', 'gid', 'mtime', 'perm', 'md5'],
	'lnk': ['targ'],
	'sock': ['uid', 'gid', 'perm'],
	'fifo': ['uid', 'gid', 'perm'],
	'blk': ['uid', 'gid', 'perm', 'devmaj', 'devmin'],
	'chr': ['uid', 'gid', 'perm', 'devmaj', 'devmin'],
	}
def compare_entries(path, a, b):
    if a['kind'] != b['kind']:
	yield "- %-20s %s" % (a['kind'], path)
	yield "+ %-20s %s" % (b['kind'], path)
	return
    misses = []
    for item in __must_match[a['kind']]:
	if not (a.has_key(item) and b.has_key(item)):
	    misses.append(item)
	elif a[item] != b[item]:
	    # Python 2.5 stat is returning subseconds, which tar
	    # doesn't backup.  We can check this later, but for now,
	    # just ignore the subsecond portions
	    if (item == 'mtime' and
		    math.floor(a[item]) == math.floor(b[item])):
		pass
	    else:
		misses.append(item)
    if misses:
	yield "  [%-18s] %s" % (",".join(misses), path)
    if 'targ' in misses:
	if a.has_key('targ'):
	    yield "  old targ: %s" % a['targ']
	if b.has_key('targ'):
	    yield "  new targ: %s" % b['targ']
    return

class check_comparer(comparer):
    """Comparer for comparing either two trees, or a tree and a
    filesystem.  'right' should be the newer tree.
    Yields strings giving the tree differences.
    """
    def handle_same_dir(self, path, a, b):
	return compare_entries(os.path.join(path, a[1]), a[2], b[2])

    def handle_delete_dir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "- %-20s %s" % ('dir', os.path.join(path, a[1]))
    def handle_add_dir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "+ %-20s %s" % ('dir', os.path.join(path, a[1]))
    def handle_same_nondir(self, path, a, b):
	return compare_entries(os.path.join(path, a[1]), a[2], b[2])

    def handle_delete_nondir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "- %-20s %s" % (a[2]['kind'], os.path.join(path, a[1]))
    def handle_add_nondir(self, path, a, recursing):
	if recursing:
	    return
	else:
	    yield "+ %-20s %s" % (a[2]['kind'], os.path.join(path, a[1]))

def update_link(assoc, path, name):
    if assoc['kind'] == 'lnk':
	assoc['targ'] = os.readlink(os.path.join(path, name))

def same_inode(a, b):
    """Do these two nodes reference what appears to be the same,
    unmodified inode."""
    return (a['kind'] == b['kind'] and
	    a['ino'] == b['ino'] and
	    a['ctime'] == b['ctime'])

class update_comparer(comparer):
    """Yields a tree equivalent to the right tree, which should be
    coming from a live filesystem.  Fills in symlink destinations and
    file md5sums (if possible)."""

    def handle_same_dir(self, path, a, b):
	yield b
	return

    def handle_add_dir(self, path, a, recursing):
	yield a
	return

    def handle_same_nondir(self, path, a, b):
	update_link(b[2], path, b[1])
	if b[2]['kind'] == 'file':
	    if same_inode(a[2], b[2]):
		b[2]['md5'] = a[2]['md5']
	    else:
		try:
		    b[2]['md5'] = hashing.hashof(os.path.join(path, b[1]))
		except OSError:
		    b[2]['md5'] = '[error]'
	yield b
	return

    def handle_add_nondir(self, path, a, recursing):
	update_link(a[2], path, a[1])
	if a[2]['kind'] == 'file':
	    try:
		a[2]['md5'] = hashing.hashof(os.path.join(path, a[1]))
	    except OSError:
		a[2]['md5'] = '[error]'
	yield a
	return

    def handle_leave(self, path, mode):
	if (mode & mode_add) != 0:
	    yield 'u',
	return

file_version = 'Asure scan version 1.1'

def read1_0(fd):
    try:
	while True:
	    yield load(fd)
    except EOFError:
	return

def read1_1(fd):
    try:
	while True:
	    for item in load(fd):
		yield item
    except EOFError:
	return

readers = {
	'Asure scan version 1.0': read1_0,
	'Asure scan version 1.1': read1_1 }

def reader(path):
    """Iterate over a previously written dump"""
    fd = gzip.open(path, 'rb')
    vers = load(fd)
    if readers.has_key(vers):
	for item in readers[vers](fd):
	    yield item
    else:
	raise "Unsupported version of asure file"
    fd.close()

use_protocol = -1

def writer_new(path, iter):
    """Write the given item (probably assembled iterator)"""
    fd = gzip.open(path, 'wb')
    dump(file_version, fd, use_protocol)
    items = []
    for item in iter:
	items.append(item)
	if len(items) >= 100:
	    dump(items, fd, use_protocol)
	    items = []
    if len(items) > 0:
	dump(items, fd, use_protocol)
    fd.close()

def writer_old(path, iter):
    """Write the given item (probably assembled iterator)"""
    fd = gzip.open(path, 'wb')
    dump('Asure scan version 1.0', fd, use_protocol)
    for item in iter:
	dump(item, fd, use_protocol)
    fd.close()

def writer(path, iter):
    writer_new(path, iter)

def rename_cycle():
    """Cycle through the names"""
    try:
	os.rename('0sure.dat.gz', '0sure.bak.gz')
    except OSError:
	pass
    os.rename('0sure.0.gz', '0sure.dat.gz')

def fresh_scan():
    """Perform a fresh scan of the filesystem"""
    tree = update_comparer(empty_tree(), walk('.'))
    writer('0sure.0.gz', tree.run())
    rename_cycle()

def check_scan():
    """Perform a scan of the filesystem, and compare it with the scan
    file.  reports differences."""
    prior = reader('0sure.dat.gz')
    cur = update_comparer(empty_tree(), walk('.')).run()
    # compare_trees(prior, cur)
    for x in check_comparer(prior, cur).run():
	print x

def update():
    """Scan filesystem, but also read the previous scan to cache md5
    hashes of files that haven't had any inode changes"""
    prior = reader('0sure.dat.gz')
    cur = update_comparer(prior, walk('.')).run()
    writer('0sure.0.gz', cur)
    rename_cycle()

def signoff():
    """Compare the previous scan with the current."""
    prior = reader('0sure.bak.gz')
    cur = reader('0sure.dat.gz')
    for x in check_comparer(prior, cur).run():
	print x

def show():
    """Show the contents of the scan file"""
    indent = 0
    for i in reader('0sure.dat.gz'):
	if i[0] == 'u':
	    indent -= 1
	print "%s%s" % ("  " * indent, i)
	if i[0] == 'd':
	    indent += 1

def nothing():
    """Just read the scan file, doing nothing with it"""
    for i in reader('0sure.dat.gz'):
	pass

def copy():
    """Copy the latest scan, can be used to update to a newer storage
    format."""
    writer('0sure.0.gz', reader('0sure.dat.gz'))
    os.rename('0sure.0.gz', '0sure.dat.gz')

commands = {
    'scan': fresh_scan,
    'update': update,
    'check': check_scan,
    'signoff': signoff,
    'show': show,
    'copy': copy,
    'nothing': nothing }

def main(argv):
    if len(argv) != 1:
	usage()
    if commands.has_key(argv[0]):
	commands[argv[0]]()
    else:
	usage()

def usage():
    print "Asure, version %s" % version.version
    print "Usage: asure {%s}" % '|'.join(commands.keys())
    sys.exit(1)

if __name__ == '__main__':
    "Test this"
    main(sys.argv[1:])
