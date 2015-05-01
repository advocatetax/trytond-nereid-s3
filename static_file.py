# -*- coding: utf-8 -*-
"""
    static_file

    Static File

    :copyright: (c) 2013-2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from boto.s3 import connection
from boto.s3 import key
from boto import exception
import base64
import json

from trytond.model import fields
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool, PoolMeta
from trytond.model import ModelView

__all__ = ['NereidStaticFolder', 'NereidStaticFile', 'UploadWizard']
__metaclass__ = PoolMeta


class NereidStaticFolder:
    __name__ = "nereid.static.folder"
    _rec_name = "folder_name"

    s3_use_bucket = fields.Boolean("Use S3 Bucket?")
    s3_access_key = fields.Char(
        "S3 Access Key",
        states={'required': Bool(Eval('s3_use_bucket'))}
    )
    s3_secret_key = fields.Char(
        "S3 Secret Key",
        states={'required': Bool(Eval('s3_use_bucket'))}
    )
    s3_bucket_name = fields.Char(
        "S3 Bucket Name",
        states={'required': Bool(Eval('s3_use_bucket'))}
    )
    s3_cloudfront_cname = fields.Char(
        "S3 Cloudfront CNAME",
        states={'required': Bool(Eval('s3_use_bucket'))}
    )
    s3_object_prefix = fields.Char("S3 Object Prefix")

    # TODO: Visible if S3
    s3_allow_large_uploads = fields.Boolean('Allow Large file uploads')
    s3_upload_form_ttl = fields.Integer('Upload form validity')

    @classmethod
    def __setup__(cls):
        super(NereidStaticFolder, cls).__setup__()

        cls._error_messages.update({
            "invalid_cname": "Cloudfront CNAME with '/' at the end is not " +
            "allowed",
            "not_s3_bucket": "The file's folder is not an S3 bucket",
            "folder_not_for_large_uploads": (
                "This file's folder does not allow large file uploads"
            ),
        })

    @classmethod
    def validate(cls, records):
        """
        Checks if cloudfront cname ends with '/'

        :param records: List of active records
        """
        super(NereidStaticFolder, cls).validate(records)
        for record in records:
            record.check_cloudfront_cname()

    def get_s3_connection(self):
        """
        Returns an active S3 connection object
        """
        return connection.S3Connection(
            self.s3_access_key, self.s3_secret_key
        )

    def get_bucket(self):
        '''
        Return an S3 bucket for the static file
        '''
        s3_conn = self.get_s3_connection()
        return s3_conn.get_bucket(self.s3_bucket_name)

    @staticmethod
    def default_s3_cloudfront_cname():
        """
        Sets default for Cloudfront CNAME
        """
        return "http://your-domain.cloudfront.net"

    def check_cloudfront_cname(self):
        """
        Checks for '/' at the end of Cloudfront CNAME
        """
        if self.s3_cloudfront_cname.endswith('/'):
            return self.raise_user_error('invalid_cname')


class NereidStaticFile:
    __name__ = "nereid.static.file"

    is_s3_bucket = fields.Function(
        fields.Boolean("S3 Bucket?"), 'get_is_s3_bucket'
    )
    s3_key = fields.Function(
        fields.Char("S3 key"), getter="get_s3_key",
        searcher="search_s3_key"
    )
    is_large_file = fields.Boolean('Is Large File')

    def get_post_form_args(self):
        """
        Returns the POST form arguments for the specific static file. It makes a
        connection to S3 via Boto and returns a dictionary, which can then be
        processed on the client side.
        """
        if not self.folder.s3_use_bucket:
            self.folder.raise_user_error('not_s3_bucket')

        if not self.folder.s3_allow_large_uploads:
            self.folder.raise_user_error('folder_not_for_large_uploads')

        conn = self.folder.get_s3_connection()
        res = conn.build_post_form_args(
            self.folder.s3_bucket_name,
            self.name,
            http_method='https',
            expires_in=self.folder.s3_upload_form_ttl,
        )
        return res

    @classmethod
    def search_s3_key(cls, name, clause):
        """
        Searcher for s3_key
        """
        if '/' in clause[-1]:
            file_name = clause[-1].split('/')[1]
        else:
            file_name = clause[-1]

        return [('name', '=', file_name)]

    def get_s3_key(self, name):
        """
        Returns s3 key for static file
        """
        if self.folder.s3_object_prefix:
            return '/'.join([self.folder.s3_object_prefix, self.name])
        else:
            return self.name

    def get_url(self, name):
        """
        Return the URL for the given static file

        :param name: Field name
        """
        if self.type == 's3':
            return '/'.join(
                [self.folder.s3_cloudfront_cname, self.s3_key]
            )
        return super(NereidStaticFile, self).get_url(name)

    def _set_file_binary(self, value):
        """
        Stores the file to amazon s3

        :param static_file: Browse record of the static file
        :param value: The value to set
        """
        if not value:
            return
        if self.type == "s3":
            if self.is_large_file:
                return
            bucket = self.folder.get_bucket()
            s3key = key.Key(bucket)
            s3key.key = self.s3_key
            return s3key.set_contents_from_string(value[:])
        return super(NereidStaticFile, self)._set_file_binary(value)

    def get_file_binary(self, name):
        '''
        Getter for the binary_file field. This fetches the file from the
        Amazon s3

        :param name: Field name
        :return: File buffer
        '''
        if self.type == "s3":
            bucket = self.folder.get_bucket()
            s3key = key.Key(bucket)
            s3key.key = self.s3_key
            try:
                return buffer(s3key.get_contents_as_string())
            except exception.S3ResponseError as error:
                if error.status == 404:
                    with Transaction().new_cursor(readonly=False) as txn:
                        self.raise_user_warning(
                            's3_file_missing',
                            'file_empty_s3'
                        )
                        # Commit cursor to clear DB records
                        txn.cursor.commit()
                    return
                raise
        return super(NereidStaticFile, self).get_file_binary(name)

    def get_file_path(self, name):
        """
        Returns path for given static file

        :param static_file: Browse record of the static file
        """
        if self.type == "s3":
            return '/'.join(
                [self.folder.s3_cloudfront_cname, self.s3_key]
            )
        return super(NereidStaticFile, self).get_file_path(name)

    @fields.depends('type')
    def on_change_type(self):
        """
        Changes the value of functional field when type is changed

        :return: Updated value of functional field
        """
        return {
            'is_s3_bucket': self.type == 's3'
        }

    def get_is_s3_bucket(self, name):
        """
        Gets value of s3_use_bucket of folder

        :param name: Field name
        :return: value of field
        """
        return bool(self.folder.s3_use_bucket)

    def check_use_s3_bucket(self):
        """
        Checks if type is S3 then folder must have use_s3_bucket
        """
        if self.type == "s3" and not self.folder.s3_use_bucket:
            return self.raise_user_error('s3_bucket_required')

    @classmethod
    def validate(cls, records):
        """
        Checks if use_s3_bucket is True for static file with type s3

        :param records: List of active records
        """
        super(NereidStaticFile, cls).validate(records)
        for record in records:
            record.check_use_s3_bucket()

    @classmethod
    @ModelView.button_action('nereid_s3.wizard_upload_large_files')
    def upload_large_file(cls, records):
        pass

    @classmethod
    def __setup__(cls):
        super(NereidStaticFile, cls).__setup__()

        s3 = ('s3', 'S3')
        if s3 not in cls.type.selection:
            cls.type.selection.append(s3)

        cls.folder.domain = [('s3_use_bucket', '=', Eval('is_s3_bucket'))]
        cls.folder.depends.append('is_s3_bucket')

        cls._error_messages.update({
            "s3_bucket_required": "Folder must have s3 bucket if type is 'S3'",
            "file_empty_s3": "The file's contents are empty on S3",
        })
        cls._buttons.update({
            'upload_large_file': {
                'invisible': ~Bool(Eval('is_large_file')),
            },
        })


class UploadWizard(Wizard):
    __name__ = 'nereid.static.file.upload_wizard'

    start = StateAction('nereid_s3.url_upload')

    # XXX: Perhaps remove hardcoding in future
    base_url = 'https://openlabs.github.io/s3uploader/v1/upload.html'

    def do_start(self, action):
        """
        This method overrides the action url given in XML and inserts the url
        in the action object. It then proceeds to return the action.
        """
        StaticFile = Pool().get('nereid.static.file')

        static_file = StaticFile(Transaction().context.get('active_id'))
        static_file.is_large_file = True
        static_file.save()

        post_args = static_file.get_post_form_args()

        action['url'] = self.base_url + '?data=' + \
            base64.b64encode(json.dumps(post_args))

        return action, {}
