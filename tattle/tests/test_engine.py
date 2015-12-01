########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import sys
import unittest

import mock

from tattle import engine
from tattle.engine import enforce_github_env_variables
from tattle.engine import parse_arguments


class GitHubEnvVariablesTestCase(unittest.TestCase):

    def test_no_env_variables(self):

        self.assertRaises(KeyError,
                          enforce_github_env_variables)

    @mock.patch.dict('os.environ', {engine.GITHUB_USER: 'u'})
    def test_one_github_env_variable(self):

        self.assertRaises(KeyError,
                          enforce_github_env_variables)

    @mock.patch.dict('os.environ', {engine.GITHUB_USER: 'u',
                                    engine.GITHUB_PASS: 'p'})
    def test_two_github_env_variables(self):

        try:
            enforce_github_env_variables()
        except KeyError:
            self.fail('Environment variables {0}, {1} should exist, '
                      'but they don\'t.'.format(engine.GITHUB_USER,
                                                engine.GITHUB_PASS)
                      )


class ParseArgumentsTestCase(unittest.TestCase):

    @mock.patch.object(sys, 'argv',
                       new=['name', '--config-path=/dir/config.yaml'])
    def test_getting_the_file_path(self):
        args = parse_arguments()
        self.assertEqual(args.config_path, '/dir/config.yaml',
                         msg='parsed the wrong config file path.')
