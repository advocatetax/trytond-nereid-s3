# -*- coding: utf-8 -*-
"""
    __init__

"""
import unittest
import trytond.tests.test_tryton

from tests.test_nereid_s3 import TestNereidS3


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestNereidS3)
    ])
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
