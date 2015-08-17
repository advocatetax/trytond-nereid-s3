#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    setup

"""
import sys
import os
import unittest
import re
import ConfigParser
from setuptools import setup, Command


class SQLiteTest(Command):
    """
    Run the tests on SQLite
    """
    description = "Run tests on SQLite"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)

        os.environ['TRYTOND_DATABASE_URI'] = 'sqlite://'
        os.environ['DB_NAME'] = ':memory:'

        from trytond.config import config
        config.add_section('nereid_s3')

        from tests import suite
        test_result = unittest.TextTestRunner(verbosity=3).run(suite())

        if test_result.wasSuccessful():
            sys.exit(0)
        sys.exit(-1)


config = ConfigParser.ConfigParser()
config.readfp(open('tryton.cfg'))
info = dict(config.items('tryton'))

for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
major_version, minor_version, _ = info.get('version', '0.0.1').split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)
module_name = 'nereid_s3'

requires = [
    'simplejson',
    'boto',
]
for dep in info.get('depends', []):
    if not re.match(r'(ir|res|webdav)(\W|$)', dep):
        requires.append(
            'trytond_%s >= %s.%s, < %s.%s' % (
                dep, major_version, minor_version, major_version,
                minor_version + 1
            )
        )
requires.append(
    'trytond >= %s.%s, < %s.%s' % (
        major_version, minor_version, major_version, minor_version + 1
    )
)

setup(
    name='fio_%s' % module_name,
    version=info.get('version', '0.0.1'),
    description='Amazon S3 backend for Nereid Static Files',
    author=info.get('author', ''),
    author_email=info.get('email', ''),
    url=info.get('website', ''),
    package_dir={'trytond.modules.%s' % module_name: '.'},
    packages=[
        'trytond.modules.%s' % module_name,
        'trytond.modules.%s.tests' % module_name,
    ],
    package_data={
        'trytond.modules.nereid_s3': info.get('xml', [])
        + ['tryton.cfg', 'view/*.xml']
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Manufacturing',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business',
    ],
    license='BSD',
    install_requires=requires,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    %s = trytond.modules.%s
    """ % (module_name, module_name),
    tests_require=[
        'mock',
    ],
    test_suite='tests',
    cmdclass={
        'test': SQLiteTest,
    },
    test_loader='trytond.test_loader:Loader',
)
