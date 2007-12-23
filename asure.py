#! /usr/bin/env python

# Directory integrity scanner.

from stat import *
import os
import sys
from os.path import join

from cPickle import dump, load

Nenter, Nleave, Nnode = range(3)

def walk(top):
    topstat = os.lstat(top)
    for x in walker(top, '.', topstat):
	yield x

def walker(root, top, topstat):
    """Directory tree generator.

    This is derived from os.walk, and is essentially the same, except
    the names are softed, and we really distinguish directories from
    files, not ever counting a symlink as a directory.  Also the
    iterator returns the 'lstat' information for each entity, since we
    will need it later.
    """

    path = join(root, top)

    try:
	names = os.listdir(path)
    except OSError:
	sys.stderr.write("Warning, can't read dir: %s\n" % path)
	return

    names.sort()

    dirs, nondirs = [], []
    for name in names:
	st = os.lstat(join(path, name))
	if S_ISDIR(st.st_mode):
	    dirs.append((name, st))
	else:
	    nondirs.append((name, st))

    yield Nenter, (top, cleanstat(topstat), [x for x,y in dirs],
	    [x for x,y in nondirs])
    for (name, st) in dirs:
	subtop = join(top, name)
	if st.st_dev == topstat.st_dev:
	    for x in walker(root, subtop, st):
		yield x
    for (name, st) in nondirs:
	subtop = join(top, name)
	yield Nnode, (subtop, cleanstat(st))
    yield Nleave, (top,)

def cleanstat(st):
    base = { 'ino': st.st_ino,
	    'mode': st.st_mode,
	    'uid': st.st_uid,
	    'gid': st.st_gid }
    return base

if __name__ == '__main__':
    "Test this"
    for mode, info in walk('/home/davidb/wd/asure'):
	# dump((mode, info), sys.stdout, 0)
	print mode, info
