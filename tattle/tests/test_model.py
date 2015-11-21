import unittest
import json

import mock

from tattle import model
from tattle.model import GitHubObject
from tattle.model import Organization
from tattle.model import Repo
from tattle.model import Branch




class GitHubObjectTestCase(unittest.TestCase):

    def test_eq(self):

        self.assertEqual(GitHubObject('a'), GitHubObject('a'))
        self.assertNotEqual(GitHubObject('a'), GitHubObject('b'))

    def test_lt(self):

        self.assertLess(GitHubObject('a'), GitHubObject('b'))
        self.assertGreater(GitHubObject('b'), GitHubObject('a'))


class OrganizationTest(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(Organization('org_name')), 'org_name')
        self.assertNotEqual(str(Organization('org_name')), 'another_org_name')

    @mock.patch('tattle.model.get_json')
    @mock.patch('os.environ')
    def test_get_num_of_repos(self, mock_environ, mock_get_json):

        org = Organization('org_name')

        mock_get_json.return_value = {model.PUBLIC_REPOS: 2,
                                      model.TOTAL_PRIVATE_REPOS: 3}

        self.assertEqual(Organization.get_num_of_repos(org), 5)





