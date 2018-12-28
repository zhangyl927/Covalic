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

import mako
import os


from girder import events
from girder.api.rest import getCurrentUser
from girder.api.v1 import resource
from girder.constants import AccessType, SettingKey, STATIC_ROOT_DIR
from girder.models.model_base import ValidationException


from girder.utility.model_importer import ModelImporter
from girder.utility.plugin_utilities import registerPluginWebroot
from .rest import challenge, phase, submission
from .constants import PluginSettings, JOB_LOG_PREFIX
from .utility import getAssetsFolder



class CustomAppRoot(ModelImporter):
    """
    The webroot endpoint simply serves the main index HTML file of covalic.
    """
    exposed = True

    indexHtml = None

    vars = {
        'apiRoot': '/api/v1',
        'staticRoot': '/static',
        'title': 'Covalic'
    }




    def GET(self):
        if self.indexHtml is None:
            self.vars['pluginCss'] = []
            self.vars['pluginJs'] = []

            builtDir = os.path.join(
                STATIC_ROOT_DIR, 'clients', 'web', 'static', 'built', 'plugins')
            plugins = self.model('setting').get(SettingKey.PLUGINS_ENABLED, ())

            for plugin in plugins:
                if os.path.exists(os.path.join(builtDir, plugin,
                                               'plugin.min.css')):
                    self.vars['pluginCss'].append(plugin)
                if os.path.exists(os.path.join(builtDir, plugin,
                                               'plugin.min.js')):
                    self.vars['pluginJs'].append(plugin)
            self.indexHtml = mako.template.Template(self.template).render(
                **self.vars)

        return self.indexHtml


def validateSettings(event):
    if event.info['key'] == PluginSettings.SCORING_USER_ID:
        if not event.info['value']:
            raise ValidationException(
                'Scoring user ID must not be empty.', 'value')
        ModelImporter.model('user').load(
            event.info['value'], force=True, exc=True)
        event.preventDefault().stopPropagation()


def challengeSaved(event):
    """
    After a challenge is saved, we want to update the Assets folder permissions
    to be the same as the challenge.
    """
    challenge = event.info
    folder = getAssetsFolder(challenge, getCurrentUser(), False)
    ModelImporter.model('folder').copyAccessPolicies(
        challenge, folder, save=True)


def onPhaseSave(event):
    """
    Hook into phase save event to synchronize access control between the phase
    and submission folders for the phase.
    """
    phase = event.info
    submissionModel = ModelImporter.model('submission', 'covalic')
    submissions = submissionModel.getAllSubmissions(phase)
    submissionModel.updateFolderAccess(phase, submissions)




def onUserSave(event):
    """
    Hook into user save event and update the user's name in their submissions.
    """
    user = event.info
    subModel = ModelImporter.model('submission', 'covalic')
    userName = subModel.getUserName(user)

    query = {
        'creatorId': user['_id']
    }
    update = {
        '$set': {
            'creatorName': userName
        }
    }
    subModel.update(query, update)


def load(info):
    resource.allowedSearchTypes.add('challenge.covalic')

    info['apiRoot'].challenge = challenge.Challenge()
    info['apiRoot'].challenge_phase = phase.Phase()
    info['apiRoot'].covalic_submission = submission.Submission()

    registerPluginWebroot(CustomAppRoot(), info['name'])

    events.bind('model.setting.validate', 'covalic', validateSettings)
    events.bind('model.challenge_challenge.save.after', 'covalic',
                challengeSaved)
    events.bind('model.challenge_phase.save.after', 'covalic',
                onPhaseSave)
    events.bind('model.user.save.after', 'covalic', onUserSave)
