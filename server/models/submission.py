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

import datetime

from girder.constants import AccessType
from girder.exceptions import GirderException
from girder.models.model_base import Model, ValidationException
from girder.plugins.covalic.utility import validateDate
from girder.plugins.covalic import scoring
from girder.plugins.worker import utils

from ..constants import PluginSettings


class Submission(Model):
    @staticmethod
    def getUserName(user):
        """Get a user's full name."""
        return user['firstName'] + ' ' + user['lastName']

    def initialize(self):
        self.name = 'covalic_submission'
        leaderboardIdx = ([
            ('phaseId', 1), ('overallScore', -1), ('approach', 1), ('latest', 1)
        ], {})
        userPhaseIdx = ([('creatorId', 1), ('phaseId', 1), ('approach', 1)], {})
        self.ensureIndices((leaderboardIdx, userPhaseIdx, 'folderId',
                            'overallScore', 'approach'))
        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'creatorId', 'creatorName', 'phaseId', 'folderId', 'created',
            'score', 'title', 'latest', 'overallScore', 'jobId', 'organization', 'organizationUrl',
            'documentationUrl', 'approach', 'meta'
        ))


    def validate(self, doc):
        if doc.get('created'):
            doc['created'] = validateDate(doc.get('created'), 'created')

        if doc.get('approach') in {'default', ''}:
            del doc['approach']

        if doc.get('score') is not None and doc.get('overallScore') is None:
            scoring.computeAverageScores(doc['score'])
            phase = self.model('phase', 'covalic').load(
                doc['phaseId'], force=True)
            doc['overallScore'] = scoring.computeOverallScore(doc, phase)
            doc['latest'] = True

            Model.update(self, query={
                'phaseId': doc['phaseId'],
                'creatorId': doc['creatorId'],
                'approach': doc.get('approach'),
                'latest': True
            }, update={
                '$set': {'latest': False}
            })

        return doc


    def createSubmission(self, creator, phase, folder, job=None, title=None,
                         created=None, organization=None, organizationUrl=None,
                         documentationUrl=None, approach=None, meta=None):
        submission = {
            'creatorId': creator['_id'],
            'creatorName': self.getUserName(creator),
            'phaseId': phase['_id'],
            'folderId': folder['_id'],
            'created': created or datetime.datetime.utcnow(),
            'score': None,
            'title': title,
            'meta': meta or {}
        }

        if organization is not None:
            submission['organization'] = organization
        if organizationUrl is not None:
            submission['organizationUrl'] = organizationUrl
        if documentationUrl is not None:
            submission['documentationUrl'] = documentationUrl
        if approach is not None:
            submission['approach'] = approach

        if job is not None:
            submission['jobId'] = job['_id']

        submission = self.save(submission)
        self.updateFolderAccess(phase, (submission,))
        return submission

    def updateFolderAccess(self, phase, submissions):
        """
        Synchronize access control between the phase and submission folders for
        the phase. Phase admins should have read access on the submission
        folders.
        """
        folderModel = self.model('folder')
        userModel = self.model('user')
        phaseModel = self.model('phase', 'covalic')

        # Get phase admin users
        phaseAcl = phaseModel.getFullAccessList(phase)
        phaseAdminUserIds = set([user['id']
                                 for user in phaseAcl.get('users')
                                 if user['level'] >= AccessType.WRITE])
        phaseAdminUsers = [userModel.load(userId, force=True, exc=True)
                           for userId in phaseAdminUserIds]

        # Update submission folder ACL for current phase admins
        try:
            for sub in submissions:
                folder = folderModel.load(sub['folderId'], force=True)
                if not folder:
                    continue
                folderAcl = folderModel.getFullAccessList(folder)

                # Revoke access to users who are not phase admins; ignore folder
                # owner
                usersToRemove = [userModel.load(user['id'], force=True,
                                                exc=True)
                                 for user in folderAcl.get('users')
                                 if (user['id'] not in phaseAdminUserIds and
                                     user['id'] != folder['creatorId'])]
                for user in usersToRemove:
                    folderModel.setUserAccess(folder, user, None)

                # Add access to phase admins; ignore folder owner
                usersToAdd = [user for user in phaseAdminUsers
                              if user['_id'] != folder['creatorId']]
                for user in usersToAdd:
                    folderModel.setUserAccess(folder, user, AccessType.READ)

                # Save folder if access changed
                if usersToRemove or usersToAdd:
                    folderModel.save(folder, validate=False)
        except TypeError:
            raise ValidationException('A list of submissions is required.')

    def scoreSubmission(self, submission, apiUrl):
        """
        Run a Girder Worker job to score a submission.
        """
        folderModel = self.model('folder')
        jobModel = self.model('job', 'jobs')
        phaseModel = self.model('phase', 'covalic')
        settingModel = self.model('setting')
        tokenModel = self.model('token')
        userModel = self.model('user')

        phase = phaseModel.load(submission['phaseId'], force=True)
        folder = folderModel.load(submission['folderId'], force=True)
        user = userModel.load(submission['creatorId'], force=True)

        otherFields = {}
        if 'overallScore' in submission:
            otherFields['rescoring'] = True

        jobTitle = '%s submission: %s' % (phase['name'], folder['name'])
        job = jobModel.createJob(
            title=jobTitle, type='covalic_score', handler='worker_handler', user=user,
            otherFields=otherFields)

        scoreUserId = settingModel.get(PluginSettings.SCORING_USER_ID)
        if not scoreUserId:
            raise GirderException(
                'No scoring user ID is set. Please set one on the plugin configuration page.')

        scoreUser = userModel.load(scoreUserId, force=True)
        if not scoreUser:
            raise GirderException('Invalid scoring user setting (%s).' % scoreUserId)

        scoreToken = tokenModel.createToken(user=scoreUser, days=7)
        folderModel.setUserAccess(
            folder, user=scoreUser, level=AccessType.READ, save=True)

        groundTruth = folderModel.load(phase['groundTruthFolderId'], force=True)

        if not phaseModel.hasAccess(phase, user=scoreUser, level=AccessType.ADMIN):
            phaseModel.setUserAccess(
                phase, user=scoreUser, level=AccessType.ADMIN, save=True)

        if not folderModel.hasAccess(groundTruth, user=scoreUser, level=AccessType.READ):
            folderModel.setUserAccess(
                groundTruth, user=scoreUser, level=AccessType.READ, save=True)

        task = phase.get('scoreTask', {})
        #image = task.get('dockerImage') or 'girder/covalic-metrics:latest'
        image = task.get('dockerImage') or 'zhangyuli927/score_test'
        containerArgs = task.get('dockerArgs') or [
            '--groundtruth=$input{groundtruth}',
            '--submission=$input{submission}'
        ]

        kwargs = {
            'task': {
                'name': jobTitle,
                'mode': 'docker',
                'docker_image': image,
                'container_args': containerArgs,
                'inputs': [{
                    'id': 'submission',
                    'type': 'string',
                    'format': 'text',
                    'target': 'filepath',
                    'filename': 'submission.zip'
                }, {
                    'id': 'groundtruth',
                    'type': 'string',
                    'format': 'text',
                    'target': 'filepath',
                    'filename': 'groundtruth.zip'
                }],
                'outputs': [{
                    'id': '_stdout',
                    'format': 'string',
                    'type': 'string'
                }]
            },
            'inputs': {
                'submission': utils.girderInputSpec(
                    folder, 'folder', token=scoreToken),
                'groundtruth': utils.girderInputSpec(
                    groundTruth, 'folder', token=scoreToken)
            },
            'outputs': {
                '_stdout': {
                    'mode': 'http',
                    'method': 'POST',
                    'format': 'string',
                    'url': '/'.join((apiUrl, 'covalic_submission',
                                     str(submission['_id']), 'score')),
                    'headers': {'Girder-Token': scoreToken['_id']}
                }
            },
            'jobInfo': utils.jobInfoSpec(job),
            'validate': False,
            'auto_convert': False,
            'cleanup': True
        }
        job['kwargs'] = kwargs
        job['covalicSubmissionId'] = submission['_id']
        job = jobModel.save(job)
        jobModel.scheduleJob(job)

        submission['jobId'] = job['_id']
        return self.save(submission, validate=False)
