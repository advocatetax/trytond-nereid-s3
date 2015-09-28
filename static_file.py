# -*- coding: utf-8 -*-
"""
    static_file

    Static File

"""
from boto.s3 import connection
from boto.s3 import key
from boto import exception
import base64
import json

from trytond.config import config
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

    is_private = fields.Boolean(
        "Is Private?", states={
            'invisible': Bool(Eval('type') != 's3'),
            'readonly': Bool(Eval('files')),
        }, depends=['type', 'files']
    )

    s3_allow_large_uploads = fields.Boolean(
        'Allow Large file uploads?',
        states={
            'invisible': Bool(Eval('type') != 's3'),
        }, depends=['type']
    )
    s3_upload_form_ttl = fields.Integer(
        'Upload form validity',
        states={
            'invisible': Bool(Eval('type') != 's3'),
        }, depends=['type']
    )

    @classmethod
    def __setup__(cls):
        super(NereidStaticFolder, cls).__setup__()

        s3 = ('s3', 'S3')
        if s3 not in cls.type.selection:
            cls.type.selection.append(s3)

        cls._error_messages.update({
            "folder_not_for_large_uploads": (
                "This file's folder does not allow large file uploads"
            ),
            'invalid_name': (
                "%s(OR) \n(3) Folder name is _private" % (
                    cls._error_messages['invalid_name'],
                )
            )
        })

    def check_name(self):
        "Check if folder name is _private"
        super(NereidStaticFolder, self).check_name()

        if self.name == '_private':
            self.raise_user_error('invalid_name')

    def get_s3_connection(self):
        """
        Returns an active S3 connection object
        """
        return connection.S3Connection(
            config.get('nereid_s3', 'access_key'),
            config.get('nereid_s3', 'secret_key')
        )

    def get_bucket(self):
        '''
        Return an S3 bucket for the static file
        '''
        s3_conn = self.get_s3_connection()
        return s3_conn.get_bucket(
            config.get('nereid_s3', 'bucket'),
        )


class NereidStaticFile:
    __name__ = "nereid.static.file"

    s3_key = fields.Function(
        fields.Char("S3 key"), getter="get_s3_key"
    )
    is_large_file = fields.Boolean('Is Large File')

    @classmethod
    def view_attributes(cls):
        return super(NereidStaticFile, cls).view_attributes() + [
            ('//group[@id="image_preview"]', 'states', {
                'invisible': Bool(Eval('is_large_file'))
            }), ('//label[@id="preview"]', 'states', {
                'invisible': ~Bool(Eval('is_large_file'))
            })]

    def get_post_form_args(self):
        """
        Returns the POST form arguments for the specific static file. It makes a
        connection to S3 via Boto and returns a dictionary, which can then be
        processed on the client side.
        """
        if self.folder.type != 's3':
            self.folder.raise_user_error('not_s3_bucket')

        if not self.folder.s3_allow_large_uploads:
            self.folder.raise_user_error('folder_not_for_large_uploads')

        conn = self.folder.get_s3_connection()
        res = conn.build_post_form_args(
            config.get('nereid_s3', 'bucket'),
            self.s3_key,
            http_method='https',
            expires_in=self.folder.s3_upload_form_ttl,
        )
        return res

    def get_s3_key(self, name):
        """
        Returns s3 key for static file
        """
        make_key_from = [self.folder.name, self.name]

        if self.folder.is_private:
            make_key_from.insert(0, '_private')

        return '/'.join(make_key_from)

    def get_url(self, name):
        """
        Return the URL for the given static file

        :param name: Field name
        """
        if self.folder.type != 's3':
            return super(NereidStaticFile, self).get_url(name)

        cloudfront = config.get('nereid_s3', 'cloudfront')
        if cloudfront:
            return '/'.join([cloudfront, self.s3_key])

        return "https://s3.amazonaws.com/%s/%s" % (
            config.get('nereid_s3', 'bucket'), self.s3_key
        )

    def _set_file_binary(self, value):
        """
        Stores the file to amazon s3

        :param static_file: Browse record of the static file
        :param value: The value to set
        """
        if not value:
            return
        if self.folder.type != "s3":
            return super(NereidStaticFile, self)._set_file_binary(value)

        if self.is_large_file:
            return
        bucket = self.folder.get_bucket()
        s3key = key.Key(bucket)
        s3key.key = self.s3_key
        return s3key.set_contents_from_string(value[:])

    def get_file_binary(self, name):
        '''
        Getter for the binary_file field. This fetches the file from the
        Amazon s3

        :param name: Field name
        :return: File buffer
        '''
        if self.folder.type == "s3":
            bucket = self.folder.get_bucket()
            s3key = bucket.lookup(self.s3_key)
            if s3key is None:
                self.raise_user_warning(
                    's3_file_missing',
                    'file_empty_s3'
                )
                return
            if s3key.size > (1000000 * 10):     # 10 MB
                # TODO: make the size configurable
                return
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
        if self.folder.type != "s3":
            return super(NereidStaticFile, self).get_file_path(name)

        cloudfront = config.get('nereid_s3', 'cloudfront')
        if cloudfront:
            return '/'.join([cloudfront, self.s3_key])

        return "https://s3.amazonaws.com/%s/%s" % (
            config.get('nereid_s3', 'bucket'), self.s3_key
        )

    @classmethod
    @ModelView.button_action('nereid_s3.wizard_upload_large_files')
    def upload_large_file(cls, records):
        pass

    @classmethod
    def __setup__(cls):
        super(NereidStaticFile, cls).__setup__()

        cls._error_messages.update({
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
    base_url = 'https://fulfilio.github.io/s3uploader/v1/upload.html'

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
