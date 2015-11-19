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

    @mock.patch.object(sys, 'argv', new=['name', '--config-path=/dir/config.yaml'])
    def test_getting_the_file_path(self):
        args = parse_arguments()
        self.assertEqual(args.config_path, '/dir/config.yaml',
                         msg='parsed the wrong config file path.')

