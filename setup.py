#! /usr/bin/env python
# Copyright 2007-2009 David Brown <asure@davidb.org>

from assurance.version import version
from distutils.core import setup

setup(name='asure',
	version=version,
	description='File integrity checker',
	author='David Brown',
	author_email='asure@davidb.org',
	url='http://github.com/d3zd3z/asure',
	scripts=['asure'],
	packages=['assurance'],
	license='GPL v2',
	long_description="""
Asure is a file integrity checker designed for verifying the integrity
of backups and other archives.
""")
