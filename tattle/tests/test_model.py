import unittest

import mock

from tattle import model

from tattle.model import GitHubObject
from tattle.model import Organization
from tattle.model import Repo
from tattle.model import Branch


class GitHubApiUrlTestCase(unittest.TestCase):

    def test_determine_number_of_threads_without_per_page(self):
        self.assertEqual(model.determine_num_of_threads(10, 10), 10)
        self.assertEqual(model.determine_num_of_threads(10, 9), 9)
        self.assertEqual(model.determine_num_of_threads(9, 10), 9)
        self.assertEqual(model.determine_num_of_threads(0, 10), 0)
        self.assertEqual(model.determine_num_of_threads(10, 0), 0)
        self.assertEqual(model.determine_num_of_threads(0, 0), 0)

    def test_determine_number_of_threads_with_per_page(self):
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=1), 10)
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=3), 4)
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=10), 1)
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=11), 1)
        self.assertEqual(model.determine_num_of_threads(0, 10, per_page=1), 0)

        self.assertRaises(ZeroDivisionError, model.determine_num_of_threads,
                          max_threads=10, num_of_items=10, per_page=0)

    @mock.patch('tattle.model.ThreadPool')
    def test_create_thread_pool(self, mock_pool):
        model.create_thread_pool(1)
        self.assertTrue(mock_pool.called)

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
        self.assertEqual(repr(Repo('repo_name', org=org)),
                         'Repo(name=repo_name,org=org_name)'
                         )

    def test_from_json(self):
        json_repo = {'name': 'repo_name',
                     'owner': {'login': 'org_name'}
                     }
        org = Organization('org_name')
        repo = Repo('repo_name', org)

        self.assertEqual(repo, Repo.from_json(json_repo))

    @mock.patch('tattle.model.logging.Logger.info')
    @mock.patch('tattle.model.Organization.get_num_of_repos')
    @mock.patch('tattle.model.QueryConfig.github_credentials')
    @mock.patch('tattle.model.Repo.get_json_repos')
    def test_get_repos(self, mock_json_repos, *args):

        mock_json_repos.return_value = \
            [{'name': 'cloudify-manager',
               'owner': {'login': 'cloudify-cosmo'}},
              {'name': 'cloudify-ui',
               'owner': {'login': 'cloudify-cosmo'}}]

        org = Organization('cloudify-cosmo')
        result = [Repo('cloudify-manager', org=org),
                  Repo('cloudify-ui', org=org)]

        self.assertEqual(Repo.get_repos(org), result)


class BranchTestCase(unittest.TestCase):

    def test_str(self):
        branch = Branch('master', Repo('cloudify-manager'))
        self.assertEqual(str(branch), 'master')

    @mock.patch('tattle.model.Branch.extract_repo_data')
    def test_from_json(self, mock_extract_repo_data):

        mock_extract_repo_data.return_value = ('getcloudify.org', Organization('cloudify-cosmo'))

        json_branch = {u'commit': {u'url': u'https://api.github.com/repos/cloudify-cosmo/getcloudify.org/commits/d87100f060e2f69f2f3702a993a2a4176b1c0493'},
                       u'name': u'CFY-2239-vcloud-plugin-docs'}

        org = Organization('cloudify-cosmo')
        repo = Repo('getcloudify.org', org=org)
        expected_branch = Branch('CFY-2239-vcloud-plugin-docs', repo)

        self.assertEqual(model.Branch.from_json(json_branch), expected_branch)

    def test_extract_repo_data(self):
        # TODO how to handle long strings like that?
        branch_url = 'https://api.github.com/repos/cloudify-cosmo/getcloudify.org/commits/d87100f060e2f69f2f3702a993a2a4176b1c0493'
        expected_extraction = ('getcloudify.org', Organization('cloudify-cosmo'))
        self.assertEqual(model.Branch.extract_repo_data(branch_url),
                         expected_extraction)

























