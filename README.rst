Trytond-nereid-s3
=================

.. image:: https://api.travis-ci.org/fulfilio/trytond-nereid-s3.png?branch=develop
  :target: https://travis-ci.org/fulfilio/trytond-nereid-s3
  :alt: Build Status
.. image:: https://pypip.in/download/fio_nereid_s3/badge.svg
    :target: https://pypi.python.org/pypi/fio_nereid_s3/
    :alt: Downloads
.. image:: https://pypip.in/version/fio_nereid_s3/badge.svg
    :target: https://pypi.python.org/pypi/fio_nereid_s3
    :alt: Latest Version
.. image:: https://pypip.in/status/fio_nereid_s3/badge.svg
    :target: https://pypi.python.org/pypi/fio_nereid_s3
    :alt: Development Status

Nereid-S3 helps to upload files to amazon-s3 from tryton layer. Files are
stored in a folder. You can create multiple folders. Folder could be public or
private.

You need to specify following options under nereid_s3 section in your tryton
configuration file::

  [nereid_s3]
  access_key =
  secret_key =
  bucket =
  cloudfront =

Internally, private folder has key prefixed with ``_private``. To
make this work, following bucket policy should be applied::

	{
	  "Version": "2008-10-17",
		"Statement": [
			{
				"Sid": "AddPerm",
				"Effect": "Allow",
				"Principal": {
					"AWS": "*"
				},
				"Action": "s3:GetObject",
				"NotResource": [
					"arn:aws:s3:::bucket_name/_private",
					"arn:aws:s3:::bucket_name/_private/*"
				]
			}
		]
	}
