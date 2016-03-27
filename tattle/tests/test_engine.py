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
    @mock.patch('tattle.engine.query_yes_no')
    def test_no_env_variables(self, mock_query_yes_no):
        mock_query_yes_no.return_value = False
        enforce_github_env_variables()
        self.assertTrue(mock_query_yes_no.called)

    @mock.patch.dict('os.environ', {engine.GITHUB_USER: 'u'})
    @mock.patch('tattle.engine.query_yes_no')
    def test_one_github_env_variable(self, mock_query_yes_no):
        mock_query_yes_no.return_value = False
        enforce_github_env_variables()
        self.assertTrue(mock_query_yes_no.called)

    @mock.patch.dict('os.environ', {engine.GITHUB_USER: 'u',
                                    engine.GITHUB_PASS: 'p'})
    @mock.patch('tattle.engine.query_yes_no')
    def test_two_github_env_variables(self, mock_query_yes_no):
        mock_query_yes_no.return_value = False
        enforce_github_env_variables()
        mock_query_yes_no.assert_not_called()


class ParseArgumentsTestCase(unittest.TestCase):
    @mock.patch.object(sys, 'argv',
                       new=['name', '--config-path=/dir/config.yaml'])
    def test_getting_the_file_path(self):
        args = parse_arguments()
        self.assertEqual(args.config_path, '/dir/config.yaml',
                         msg='parsed the wrong config file path.')
