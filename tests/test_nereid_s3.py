# -*- coding: utf-8 -*-
"""
    test_nereid_s3

    Test Nereid-S3

"""

import sys
import os
DIR = os.path.abspath(
    os.path.normpath(
        os.path.join(__file__, '..', '..', '..', '..', '..', 'trytond')
    )
)
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest

import boto
from moto import mock_s3
import trytond.tests.test_tryton
from trytond.tests.test_tryton import (
    POOL, DB_NAME, USER, CONTEXT, ModuleTestCase
)
from trytond.transaction import Transaction
from trytond.config import config

config.set('nereid_s3', 's3_access_key', 'ABCD')
config.set('nereid_s3', 's3_secret_key', '123XYZ')
config.set('nereid_s3', 'bucket', 'tryton-test-s3')


class TestNereidS3(ModuleTestCase):
    '''
    Test Nereid S3
    '''

    module = 'nereid_s3'

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid_s3')
        self.static_file = POOL.get('nereid.static.file')
        self.static_folder = POOL.get('nereid.static.folder')

        self.mock = mock_s3()
        self.mock.start()

        # Create test bucket to save s3 data
        conn = boto.connect_s3()
        conn.create_bucket(config.get('nereid_s3', 'bucket'))

    def tearDown(self):
        self.mock.stop()

    def test0010_static_file(self):
        """
        Checks that file is saved to amazon s3
        """
        with Transaction().start(DB_NAME, USER, context=CONTEXT):

            # Create folder for amazon s3
            folder, = self.static_folder.create([{
                'name': 's3store',
                'description': 'S3 Folder',
                'type': 's3',
            }])
            self.assert_(folder.id)

            s3_folder = self.static_folder.search([
                ('type', '=', 's3')
            ])[0]

            # Create static file for amazon s3 bucket
            file, = self.static_file.create([{
                'name': 'testfile.png',
                'folder': s3_folder,
                'file_binary': buffer('testfile')
            }])
            self.assert_(file.id)

            self.assertEqual(
                file.file_binary, buffer('testfile')
            )


def suite():
    """
    Define Test suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestNereidS3)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
