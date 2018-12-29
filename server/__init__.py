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

from girder.api.v1 import resource


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


def load(info):
    resource.allowedSearchTypes.add('challenge.covalic')

    info['apiRoot'].challenge = challenge.Challenge()
    info['apiRoot'].challenge_phase = phase.Phase()
    info['apiRoot'].covalic_submission = submission.Submission()

    registerPluginWebroot(CustomAppRoot(), info['name'])

