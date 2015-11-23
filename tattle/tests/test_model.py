import unittest
import json

import mock

from tattle import model

from tattle.model import GitHubObject
from tattle.model import Organization
from tattle.model import Repo


class GitHubApiUrlTestCase(unittest.TestCase):

    def test_pagination_format(self):
        pagination_string = '?page=1&per_page=100'
        self.assertEqual(pagination_string, model.pagination_format(1))

    def test_generate_github_api_url_with_organization(self):

        url = 'https://api.github.com/orgs/cloudify-cosmo'
        self.assertEqual(model.generate_github_api_url('organization',
                                                       org_name='cloudify-cosmo'),
                         url)

    @mock.patch('tattle.model.pagination_format')
    def test_generate_github_api_url_with_repos(self, mock_pagination_format):

        mock_pagination_format.return_value = '?page=1&per_page=100'
        url = 'https://api.github.com/orgs/cloudify-cosmo/repos' \
              '?page=1&per_page=100'

        self.assertEqual(model.generate_github_api_url('repos',
                                                       org_name='cloudify-cosmo'
                                                       ),
                         url)

    def test_generate_github_api_url_with_list_branches(self):

        url = 'https://api.github.com/repos/cloudify-cosmo/cloudify-manager/branches'
        self.assertEqual(model.generate_github_api_url('list_branches',
                                                       org_name='cloudify-cosmo',
                                                       repo_name='cloudify-manager'),
                         url)

    def test_generate_github_api_url_with_detailed_branch(self):

        url = 'https://api.github.com/repos/cloudify-cosmo/cloudify-manager/branches/master'
        self.assertEqual(model.generate_github_api_url('detailed_branch',
                                                       org_name='cloudify-cosmo',
                                                       repo_name='cloudify-manager',
                                                       branch_name='master'),
                         url)















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


class RepoTest(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(Repo('repo_name')), 'repo_name')
        self.assertNotEqual(str(Repo('repo_name')), 'another_repo_name')

    def test_repr(self):
        org = Organization('org_name')
        self.assertEqual(repr(Repo('repo_name', organization=org)),
                         'Repo(name=repo_name,organization=org_name)'
                         )

    def test_from_json(self):
        json_repo = json.loads('{"name" : "repo_name",'
                               '"owner": {'
                               '"login": "org_name"'
                               '}}')
        org = Organization('org_name')
        repo = Repo('repo_name', org)

        self.assertEqual(repo, Repo.from_json(json_repo))














