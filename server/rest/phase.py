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


from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import filtermodel, loadmodel, getApiUrl, Resource, \
    RestException
from girder.constants import AccessType



class Phase(Resource):
    def __init__(self):
        super(Phase, self).__init__()

        self.resourceName = 'challenge_phase'

        self.route('POST', (), self.createPhase)

    @access.user
    @loadmodel(map={'challengeId': 'challenge'}, level=AccessType.WRITE,
               model='challenge', plugin='covalic')
    @describeRoute(
        Description('Add a phase to an existing challenge.')
        .param('challengeId', 'The ID of the challenge to add the phase to.')
        .param('name', 'The name for this phase.')
        .param('description', 'Description for this phase.', required=False)
        .param('instructions', 'Instructions to participants for this phase.',
               required=False)
        .param('participantGroupId', 'If you wish to use an existing '
               'group as the participant group, pass its ID in this parameter.'
               ' If you omit this, a participant group will be automatically '
               'created for this phase.', required=False)
        .param('public', 'Whether the phase should be publicly visible.',
               dataType='boolean')
        .param('active', 'Whether the phase will accept and score additional '
               'submissions.', dataType='boolean', required=False)
        .param('startDate', 'The start date of the phase (ISO 8601 format).',
               dataType='dateTime', required=False)
        .param('endDate', 'The end date of the phase (ISO 8601 format).',
               dataType='dateTime', required=False)
        .param('type', 'The type of the phase.', required=False)
        .param('hideScores', 'Whether submission scores should be hidden from '
               'participants.', dataType='boolean', default=False,
               required=False)
        .param('matchSubmissions', 'Whether to require that submission '
               'filenames match ground truth filenames', dataType='boolean',
               default=True, required=False)
        .param('enableOrganization', 'Enable submission Organization field.', dataType='boolean',
               default=False, required=False)
        .param('enableOrganizationUrl', 'Enable submission Organization URL field.',
               dataType='boolean', default=False, required=False)
        .param('enableDocumentationUrl', 'Enable submission Documentation URL field.',
               dataType='boolean', default=False, required=False)
        .param('requireOrganization', 'Require submission Organization field.', dataType='boolean',
               default=True, required=False)
        .param('requireOrganizationUrl', 'Require submission Organization URL field.',
               dataType='boolean', default=True, required=False)
        .param('requireDocumentationUrl', 'Require submission Documentation URL field.',
               dataType='boolean', default=True, required=False)
        .param('meta', 'A JSON object containing additional metadata.',
               required=False)
    )
    def createPhase(self, challenge, params):
        self.requireParams('name', params)

        user = self.getCurrentUser()
        public = self.boolParam('public', params, default=False)
        active = self.boolParam('active', params, default=False)
        hideScores = self.boolParam('hideScores', params, default=False)
        matchSubmissions = self.boolParam('matchSubmissions', params,
                                          default=True)
        enableOrganization = self.boolParam('enableOrganization', params, default=False)
        enableOrganizationUrl = self.boolParam('enableOrganizationUrl', params, default=False)
        enableDocumentationUrl = self.boolParam('enableDocumentationUrl', params, default=False)
        requireOrganization = self.boolParam('requireOrganization', params, default=True)
        requireOrganizationUrl = self.boolParam('requireOrganizationUrl', params, default=True)
        requireDocumentationUrl = self.boolParam('requireDocumentationUrl', params, default=True)
        description = params.get('description', '').strip()
        instructions = params.get('instructions', '').strip()

        participantGroupId = params.get('participantGroupId')
        if participantGroupId:
            group = self.model('group').load(
                participantGroupId, user=user, level=AccessType.READ)
        else:
            group = None

        ordinal = len([self.model('phase', 'covalic').filter(p, user)
                       for p in self.model('phase', 'covalic').list(
                           challenge, user=user)])

        startDate = params.get('startDate')
        endDate = params.get('endDate')

        type = params.get('type', '').strip()
        meta = _loadMetadata(params)

        phase = self.model('phase', 'covalic').createPhase(
            name=params['name'].strip(), description=description,
            instructions=instructions, active=active, public=public,
            creator=user, challenge=challenge, participantGroup=group,
            ordinal=ordinal, startDate=startDate, endDate=endDate,
            type=type, hideScores=hideScores, matchSubmissions=matchSubmissions,
            enableOrganization=enableOrganization, enableOrganizationUrl=enableOrganizationUrl,
            enableDocumentationUrl=enableDocumentationUrl,
            requireOrganization=requireOrganization,
            requireOrganizationUrl=requireOrganizationUrl,
            requireDocumentationUrl=requireDocumentationUrl,
            meta=meta
        )

        return phase
