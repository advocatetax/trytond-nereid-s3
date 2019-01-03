# -*- coding: utf-8 -*-
"""
    test_nereid_s3

    Test Nereid-S3

"""
import unittest

import boto
from moto import mock_s3_deprecated
import trytond.tests.test_tryton
from trytond.tests.test_tryton import with_transaction, ModuleTestCase
from trytond.pool import Pool
from trytond.config import config

config.set('nereid_s3', 's3_access_id', 'ABCD')
config.set('nereid_s3', 's3_secret_key', '123XYZ')
config.set('nereid_s3', 'bucket', 'tryton-test-s3')


class TestNereidS3(ModuleTestCase):
    '''
    Test Nereid S3
    '''

    module = 'nereid_s3'

    @with_transaction()
    @mock_s3_deprecated
    def test0010_static_file(self):
        """
        Checks that file is saved to amazon s3
        """
        StaticFile = Pool().get('nereid.static.file')
        StaticFolder = Pool().get('nereid.static.folder')

        # Create test bucket to save s3 data
        conn = boto.connect_s3()
        conn.create_bucket(config.get('nereid_s3', 'bucket'))

        # Create folder for amazon s3
        folder, = StaticFolder.create([{
            'name': 's3store',
            'description': 'S3 Folder',
            'type': 's3',
        }])
        self.assertTrue(folder.id)

        s3_folder = StaticFolder.search([
            ('type', '=', 's3')
        ])[0]

        # Create static file for amazon s3 bucket
        file, = StaticFile.create([{
            'name': 'testfile.png',
            'folder': s3_folder,
            'file_binary': b'testfile'
        }])
        self.assertTrue(file.id)

        self.assertEqual(
            file.file_binary, b'testfile'
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
