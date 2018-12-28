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

# from girder.utility.model_importer import ModelImporter


# def _getUser(userId):
#     """Convenience function to get a user document from a user ID."""
#     user = ModelImporter.model('user').load(userId, force=True)
#     return user
#
#
# # def _getUsers(acl, accessLevel):
# #     """
# #     Given an access list and an access level, return a list of the users at or
# #     above the access level in the access list.
# #
# #     :param acl: an access list such as that returned by
# #         AccessControlledModel.getFullAccessList()
# #     :type acl: dict
# #     :param accessLevel: the minimum access level
# #     :type accessLevel: girder.AccessType
# #     """
# #     users = [_getUser(user['id']) for user
# #              in acl.get('users', None)
# #              if user['level'] >= accessLevel]
# #     return users



