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
from girder.api.rest import filtermodel, loadmodel, Resource, RestException


class Challenge(Resource):
    def __init__(self):
        super(Challenge, self).__init__()

        self.resourceName = 'challenge'

        self.route('POST', (), self.createChallenge)


    @access.user
    @filtermodel(model='challenge', plugin='covalic')
    @describeRoute(
        Description('Create a new challenge.')
        .param('name', 'The name for this challenge.')
        .param('description', 'Description for this challenge.', required=False)
        .param('instructions', 'Instructional text for this challenge.',
               required=False)
        .param('public', 'Whether the challenge should be publicly visible.',
               dataType='boolean')
        .param('organizers', 'The organizers of the challenge.',
               required=False)
        .param('startDate', 'The start date of the challenge '
               '(ISO 8601 format).', dataType='dateTime', required=False)
        .param('endDate', 'The end date of the challenge (ISO 8601 format).',
               dataType='dateTime', required=False)
    )
    def createChallenge(self, params):
        self.requireParams('name', params)
        user = self.getCurrentUser()
        public = self.boolParam('public', params, default=False)
        description = params.get('description', '').strip()
        instructions = params.get('instructions', '').strip()
        organizers = params.get('organizers', '').strip()
        startDate = params.get('startDate')
        endDate = params.get('endDate')

        return self.model('challenge', 'covalic').createChallenge(
            name=params['name'].strip(), description=description, public=public,
            instructions=instructions, creator=user, organizers=organizers,
            startDate=startDate, endDate=endDate)

