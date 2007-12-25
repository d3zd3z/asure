#! /usr/bin/env python

import md5
import sys
import os
import platform
import base64

# Fast hashing of files.
# Initial implementation isn't intended to be fast, just work.
#
# TODO:
#  - Use mmap() in cases where that would work.  Not sure this would
#    really be any faster.
#  - Optionally bind to faster MD5 library.

# When running on Linux, and root, avoid updating the atime of the
# file.
extra_flags = 0
if platform.system() == 'Linux' and os.getuid() == 0:
    extra_flags = 01000000

def hashof(path):
    ufd = os.open(path, os.O_RDONLY | extra_flags)
    fd = os.fdopen(ufd, 'rb', 0)
    # fd = open(path, 'rb')
    hash = md5.new()
    while True:
	buf = fd.read(32768)
	if buf == '':
	    break
	hash.update(buf)
    fd.close()
    return hash.digest()

if __name__ == '__main__':
    for name in sys.argv[1:]:
	print ("%s  %s" % (base64.b16encode(hashof(name)), name))
