'''
    trytond_nereid_s3 init file

    Tryton module to support Nereid-S3 for Amazon S3 storage

:copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited.
:license: GPLv3, see LICENSE for more details
'''
from trytond.pool import Pool
from static_file import NereidStaticFolder, NereidStaticFile, UploadWizard


def register():
    Pool.register(
        NereidStaticFolder,
        NereidStaticFile,
        module='nereid_s3', type_='model')

    Pool.register(
        UploadWizard,
        module='nereid_s3', type_='wizard'
    )
