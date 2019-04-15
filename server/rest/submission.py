#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import cherrypy
import os

from ..models.phase import Phase
from ..models.submission import Submission
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import Resource, filtermodel, loadmodel
from girder.constants import AccessType, SortDir
from girder.exceptions import AccessException, GirderException, RestException, ValidationException
from girder.models.folder import Folder


class Submission(Resource):
    def __init__(self):
        super(Submission, self).__init__()

        self.resourceName = 'covalic_submission'

        self.route('POST', (), self.postSubmission)
        self.route('POST', (':id', 'score'), self.postScore)

    def _checkRequireParam(self, phase, params, paramName, requireOptionName):
        """
        Require a parameter conditionally, based on a phase property.

        :param phase: The phase.
        :param params: Parameters.
        :param paramName: Parameter name.
        :param requireOptionName: Phase property that indicates whether the parameter is required.
        """
        if phase.get(requireOptionName, False):
            self.requireParams(paramName, params)

    def _getStrippedParam(self, params, name):
        """
        Return the stripped parameter, or None if the parameter doesn't exist.

        :param params: Parameters.
        :param name: Parameter name.
        :return: The stripped parameter, or None.
        """
        param = params.get(name)
        if param is not None:
            param = param.strip()
        return param


    @access.public
    @filtermodel(model=Submission)
    @autoDescribeRoute(
        Description('Make a submission to the challenge.')
        .modelParam('phaseId', 'The ID of the challenge phase to submit to.',
                    model=Phase, level=AccessType.READ, paramType='query',
                    destName='phase')
        .modelParam('folderId', 'The folder ID containing the submission data.',
                    model=Folder, level=AccessType.ADMIN, paramType='query',
                    destName='folder')
        .param('title', 'Title for the submission')
        .param('date', 'The date of the submission.', required=False)
        .param('userId', 'The ID of the user to submit on behalf of.',
               required=False)
        #.param('organization', 'Organization associated with the submission.', required=False)
        #.param('organizationUrl', 'URL for organization associated with the submission.',
         #      required=False)
        #.param('documentationUrl', 'URL of documentation associated with the submission.',
         #      required=False)
        #.param('approach', 'The submission approach.', required=False)
        #.jsonParam('meta', 'A JSON object containing additional submission metadata.',
         #          paramType='form', requireObject=True, required=False)
        #.errorResponse('You are not a member of the participant group.', 403)
        #.errorResponse('The ID was invalid.')
    )
    def postSubmission(self, phase, folder, **params):
        user = self.getCurrentUser()

        if not phase.get('active') and (not user or not user.get('admin')):
            raise ValidationException('You may not submit to this phase '
                                      'because it is not currently active.')

        self.requireParams('title', params)
        title = self._getStrippedParam(params, 'title')

        # Only users in the participant group (or with write access) may submit
        if phase['participantGroupId'] not in user['groups']:
            self.model('phase', 'covalic').requireAccess(
                phase, user, level=AccessType.WRITE)


        #approach = self._getStrippedParam(params, 'approach')

        # Site admins may override the submission creation date
        created = None
        if params['date'] is not None:
            self.requireAdmin(user, 'Administrator access required to override '
                                    'the submission creation date.')
            created = params['date']

        # Site admins may submit on behalf of another user
        if params['userId'] is not None:
            self.requireAdmin(user, 'Administrator access required to submit '
                                    'to this phase on behalf of another user.')
            user = self.model('user').load(params['userId'], force=True,
                                           exc=True)

        submissionModel = self.model('submission', 'covalic')

        submission = submissionModel.createSubmission(
            creator=user,
            phase=phase,
            folder=folder,
            job=None,
            title=title,
            created=created,
            #approach=approach,
            meta=params.get('meta'))

        apiUrl = os.path.dirname(cherrypy.url())

        try:
            submission = submissionModel.scoreSubmission(submission, apiUrl)
        except GirderException:
            submissionModel.remove(submission)
            raise

        return submission

    @access.public
    @autoDescribeRoute(
        Description('Post a score for a given submission.')
        .modelParam('id', model='submission', plugin='covalic')
        .jsonParam(
            'score', 'The JSON object containing the scores for this submission.',
            paramType='body',
            schema={
                "$schema": "http://json-schema.org/schema#",
                'type': 'array',
                'items': {'$ref': '#/definitions/score'},
                'definitions': {
                    'score': {
                        'type': 'object',
                        'properties': {
                            'dataset': {'type': 'string'},
                            'metrics': {
                                'type': 'array',
                                'items': {'$ref': '#/definitions/metric'}
                            }
                        },
                        'required': ['dataset', 'metrics']
                    },
                    'metric': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'value': {'type': ['null', 'number', 'string']}
                        },
                        'required': ['name', 'value']
                    }
                }
            })
        .notes('This should only be called by the scoring service, not by '
               'end users.')
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.'))
        .errorResponse('Admin access was denied for the challenge phase.', 403)
    )
    def postScore(self, submission, score, params):
        # Ensure admin access on the containing challenge phase
        phase = self.model('phase', 'covalic').load(
            submission['phaseId'], user=self.getCurrentUser(), exc=True,
            level=AccessType.ADMIN)

        # Record whether submission is being re-scored
        rescoring = 'overallScore' in submission

        # Save document to trigger computing overall score
        submission.pop('overallScore', None)
        submission['score'] = score
        submission = self.model('submission', 'covalic').save(submission)

        #########################################################  step1


        ############################################
        ######### 第一次嘗試
        from girder.models.upload import Upload
        from girder.api.v1.file import File
        from girder.utility import RequestBodyStream
        import six


        dest = dict(submission)
        # for i in range(5000):
        #     dest.setdefault(i, i + 20)

        dest1 = str(dest)
        size = len(dest1)

        user = self.model('user').load(submission['creatorId'], force=True)
        #str1 = submission['title']
        # str2 = '.txt'
        # name = "".join((str1, str2))
        name = submission['title']

        parentType = 'folder'
        parentId = submission['folderId']
        parent = self.model(parentType).load(
            id=parentId, user=user, level=AccessType.ADMIN, exc=True)

        mimeType = u'image/png'
        reference = None

        File().requireParams({'size': size})
        assetstore = None

        chunk = None
        if size > 0 and cherrypy.request.headers.get('Content-Length'):
            ct = cherrypy.request.body.content_type.value
            #if (ct not in cherrypy.request.body.processors and
             #       ct.split('/', 1)[0] not in cherrypy.request.body.processors):
              #  chunk = RequestBodyStream(cherrypy.request.body)
        if chunk is not None and chunk.getSize() <= 0:
            chunk = None

        try:
            # TODO: This can be made more efficient by adding
            #    save=chunk is None
            # to the createUpload call parameters.  However, since this is
            # a breaking change, that should be deferred until a major
            # version upgrade.
            upload = Upload().createUpload(
                user=user, name=name, parentType=parentType, parent=parent, size=size,
                mimeType=mimeType, reference=reference, assetstore=assetstore)
        except OSError as exc:
            if exc.errno == errno.EACCES:
                raise GirderException(
                    'Failed to create upload.', 'girder.api.v1.file.create-upload-failed')
            raise
        if upload['size'] > 0:
            if chunk:
                return Upload().handleChunk(upload, chunk, filter=True, user=user)

        else:
            return self._model.filter(Upload().finalizeUpload(upload), user)

        offset = 0

        if 'chunk' in params:
            chunk = params['chunk']
            if isinstance(chunk, cherrypy._cpreqbody.Part):
                # Seek is the only obvious way to get the length of the part
                chunk.file.seek(0, os.SEEK_END)
                size = chunk.file.tell()
                chunk.file.seek(0, os.SEEK_SET)
                chunk = RequestBodyStream(chunk.file, size=size)
        else:
            chunk = RequestBodyStream(six.BytesIO(dest1), len(dest1))
            #chunk = FileHandle(dest1)

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        if upload['received'] != offset:
            raise RestException(
                'Server has received %s bytes, but client sent offset %s.' % (
                    upload['received'], offset))
        try:
            Upload().handleChunk(upload, chunk, filter=True, user=user)
        except IOError as exc:
            if exc.errno == errno.EACCES:
                raise Exception('Failed to store upload.')
            raise

        ##########################################################################

        # Delete the scoring user's job token since the job is now complete.
        token = self.getCurrentToken()
        self.model('token').remove(token)

        return submission

