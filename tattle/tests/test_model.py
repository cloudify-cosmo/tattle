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

import unittest

import mock
import yaml

from tattle import model

from tattle.model import GitHubObject
from tattle.model import Organization
from tattle.model import Repo
from tattle.model import Branch
from tattle.model import Issue
from tattle.model import Filter
from tattle.model import NameFilter
from tattle.model import IssueFilter
from tattle.model import Transform
from tattle.model import QueryConfig
from tattle.model import Query
from tattle.model import BranchQuery


class GitHubApiUrlTestCase(unittest.TestCase):

    def test_determine_number_of_threads_without_per_page(self):
        self.assertEqual(model.determine_num_of_threads(10, 10), 10)
        self.assertEqual(model.determine_num_of_threads(10, 9), 9)
        self.assertEqual(model.determine_num_of_threads(9, 10), 9)
        self.assertEqual(model.determine_num_of_threads(0, 10), 0)
        self.assertEqual(model.determine_num_of_threads(10, 0), 0)
        self.assertEqual(model.determine_num_of_threads(0, 0), 0)

    def test_determine_number_of_threads_with_per_page(self):
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=1),
                         10)
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=3),
                         4)
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=10),
                         1)
        self.assertEqual(model.determine_num_of_threads(10, 10, per_page=11),
                         1)
        self.assertEqual(model.determine_num_of_threads(0, 10, per_page=1),
                         0)

        self.assertRaises(ZeroDivisionError, model.determine_num_of_threads,
                          thread_limit=10, num_of_items=10, per_page=0)

    @mock.patch('tattle.model.ThreadPool')
    def test_create_thread_pool(self, mock_pool):
        model.create_thread_pool(1)
        self.assertTrue(mock_pool.called)

    def test_pagination_format(self):
        pagination_string = '?page=1&per_page=100'
        self.assertEqual(pagination_string, model.pagination_format(1))

    def test_generate_github_api_url_with_organization(self):

        url = 'https://api.github.com/orgs/cloudify-cosmo'
        self.assertEqual(
            model.generate_github_api_url('organization',
                                          org_name='cloudify-cosmo'),
            url)

    @mock.patch('tattle.model.pagination_format')
    def test_generate_github_api_url_with_repos(self,
                                                mock_pagination_format):

        mock_pagination_format.return_value = '?page=1&per_page=100'
        url = 'https://api.github.com/orgs/cloudify-cosmo/repos' \
              '?page=1&per_page=100'

        self.assertEqual(
            model.generate_github_api_url('repos',
                                          org_name='cloudify-cosmo'
                                          ),
            url)

    def test_generate_github_api_url_with_list_branches(self):

        url = ('https://api.github.com/repos/cloudify-cosmo/'
               'cloudify-manager/branches')
        self.assertEqual(
            model.generate_github_api_url('list_branches',
                                          org_name='cloudify-cosmo',
                                          repo_name='cloudify-manager'),
            url)

    def test_generate_github_api_url_with_detailed_branch(self):

        url = ('https://api.github.com/repos/cloudify-cosmo'
               '/cloudify-manager/branches/master')
        self.assertEqual(
            model.generate_github_api_url('detailed_branch',
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
    @mock.patch('tattle.model.Organization.get_num_of_repos', return_value=1)
    @mock.patch('multiprocessing.pool.ThreadPool.map')
    def test_get_repos(self, mock_map, *args):
        mock_map.return_value = \
            [[{'name': 'cloudify-manager',
               'owner': {'login': 'cloudify-cosmo'}}],
             [{'name': 'cloudify-ui',
               'owner': {'login': 'cloudify-cosmo'}}]]

        org = Organization('cloudify-cosmo')
        expected_result = [Repo('cloudify-manager', org=org),
                           Repo('cloudify-ui', org=org)]
        result = Repo.get_repos(org)
        self.assertEqual(result, expected_result)


class BranchTestCase(unittest.TestCase):

    def test_str(self):
        branch = Branch('master', Repo('cloudify-manager'))
        self.assertEqual(str(branch), 'master')

    @mock.patch('tattle.model.Branch.extract_repo_data')
    def test_from_json(self, mock_extract_repo_data):

        mock_extract_repo_data.return_value = ('getcloudify.org',
                                               Organization('cloudify-cosmo'))

        json_branch = {u'commit': {u'url': (u'https://api.github.com/'
                                            u'repos/cloudify-cosmo/'
                                            u'getcloudify.org/commits/'
                                            u'd87100f060e2f69f2f3702a99'
                                            u'3a2a4176b1c0493')},
                       u'name': u'CFY-2239-vcloud-plugin-docs'}

        org = Organization('cloudify-cosmo')
        repo = Repo('getcloudify.org', org=org)
        expected_branch = Branch('CFY-2239-vcloud-plugin-docs', repo)

        self.assertEqual(model.Branch.from_json(json_branch), expected_branch)

    def test_extract_repo_data(self):
        # TODO how to handle long strings like that?
        branch_url = ('https://api.github.com/repos/cloudify-cosmo/'
                      'getcloudify.org/commits/'
                      'd87100f060e2f69f2f3702a993a2a4176b1c0493')
        expected_extraction = ('getcloudify.org',
                               Organization('cloudify-cosmo'))
        self.assertEqual(model.Branch.extract_repo_data(branch_url),
                         expected_extraction)

    @mock.patch('tattle.model.logging.Logger.info')
    @mock.patch('multiprocessing.pool.ThreadPool.map')
    def test_get_org_branches(self, mock_map, *args):
        self.maxDiff = None
        mock_map.return_value = [
            [{u'commit': {u'url': u'https://api.github.com/repos/'
                                  u'cloudify-cosmo/getcloudify.org/'
                                  u'commits/d87100f060e2f69f2f3702a'
                                  u'993a2a4176b1c0493'},
              u'name': u'CFY-2239-vcloud-plugin-docs'},
             {u'commit': {u'url': u'https://api.github.com/repos/'
                                  u'cloudify-cosmo/getcloudify.org/'
                                  u'commits/955c56daf6e43809886d1ce'
                                  u'e2516a9d7c1d1f5fc'},
              u'name': u'agent-refactoring-project'}
             ],
            [{u'commit': {u'url': u'https://api.github.com/repos/'
                                  u'cloudify-cosmo/gs-ui-infra/'
                                  u'commits/b66e74f1de35334ae6519f4'
                                  u'f3b26022fb6e38557'},
              u'name': u'3.2.0-build'},
             {u'commit': {u'url': u'https://api.github.com/repos/'
                                  u'cloudify-cosmo/gs-ui-infra/'
                                  u'commits/0095ef1cdaf9df8fa24cef2'
                                  u'51bbfbc60acd54818'},
              u'name': u'3.3rc1-build'}
             ]
        ]
        expected_result = [Branch(u'3.2.0-build',
                                  Repo(u'gs-ui-infra',
                                       org=Organization(u'cloudify-cosmo'))),
                           Branch(u'3.3rc1-build',
                                  Repo(u'gs-ui-infra',
                                       org=Organization(u'cloudify-cosmo'))),
                           Branch(u'CFY-2239-vcloud-plugin-docs',
                                  Repo(u'getcloudify.org',
                                       org=Organization(u'cloudify-cosmo'))),
                           Branch(u'agent-refactoring-project',
                                  Repo(u'getcloudify.org',
                                       org=Organization(u'cloudify-cosmo')))
                           ]
        org = Organization('org_name')
        repos = [Repo('repo_name')]
        self.assertEqual(model.Branch.get_org_branches(repos, org),
                         expected_result)

    def test_update_branches_with_issues(self):

        branches = [Branch(u'CFY-3223-allow-external-rabbitmq',
                           Repo(u'cloudify-manager',
                                org=Organization(u'cloudify-cosmo'))),
                    Branch(u'CFY-3502-ngmin-faster',
                           Repo(u'cloudify-ui',
                                org=Organization(u'cloudify-cosmo')))]

        issues = [Issue('CFY-3223', 'Resolved'),
                  Issue('CFY-3502', 'Closed')]

        expected_branches = [Branch(u'CFY-3223-allow-external-rabbitmq',
                                    Repo(u'cloudify-manager',
                                         org=Organization(u'cloudify-cosmo')),
                                    jira_issue=Issue('CFY-3223', 'Resolved')),
                             Branch(u'CFY-3502-ngmin-faster',
                                    Repo(u'cloudify-ui',
                                         org=Organization(u'cloudify-cosmo')),
                                    jira_issue=Issue('CFY-3502', 'Closed'))
                             ]
        Branch.update_branches_with_issues(branches, issues)
        self.assertEqual(branches, expected_branches)

    def test_update_branches_with_issues_empty_branches(self):

        branches = []
        issues = [Issue('CFY-3223', 'Resolved')]

        expected_branches = []

        Branch.update_branches_with_issues(branches, issues)
        self.assertEqual(branches, expected_branches)

    def test_update_branches_with_issues_empty_issues(self):

        branches = [Branch(u'CFY-3223-allow-external-rabbitmq',
                           Repo(u'cloudify-manager',
                                org=Organization(u'cloudify-cosmo')))
                    ]
        issues = []

        expected_branches = [Branch(u'CFY-3223-allow-external-rabbitmq',
                                    Repo(u'cloudify-manager',
                                         org=Organization(u'cloudify-cosmo')))
                             ]

        Branch.update_branches_with_issues(branches, issues)
        self.assertEqual(branches, expected_branches)

    def test_update_details_with_correctly_formatted_details(self):

        branch = Branch(u'CFY-3223-allow-external-rabbitmq',
                        Repo(u'cloudify-manager',
                             org=Organization(u'cloudify-cosmo')))

        details = {'commit': {
            'commit': {
                'author': {
                    'email': 'avia@gigaspaces.com'
                }}}}
        expected_branch = Branch(u'CFY-3223-allow-external-rabbitmq',
                                 Repo(u'cloudify-manager',
                                      org=Organization(u'cloudify-cosmo')),
                                 committer_email='avia@gigaspaces.com')
        Branch.update_details(branch, details)
        self.assertEqual(branch, expected_branch)

    def test_update_details_with_incorrectly_formatted_details(self):

        branch = Branch(u'CFY-3223-allow-external-rabbitmq',
                        Repo(u'cloudify-manager',
                             org=Organization(u'cloudify-cosmo')))

        details = {'commit': {
            'commit': {
                'author': {
                    'not_email': 'no_email'
                }}}}

        self.assertRaises(KeyError, Branch.update_details, branch, details)


class IssueTestCase(unittest.TestCase):

    def test_eq(self):

        issue1 = Issue(u'CFY-3223', u'Closed')
        issue2 = Issue(u'CFY-3502', u'Closed')
        issue3 = Issue(u'CFY-3223', u'Resolved')
        issue4 = Issue(u'CFY-3223', u'Closed')

        self.assertNotEqual(issue1, issue2)
        self.assertNotEqual(issue2, issue3)
        self.assertNotEqual(issue1, issue3)
        self.assertEqual(issue1, issue4)

    def test_str(self):

        issue = Issue(u'CFY-3223', u'Closed')
        expected_string = 'key: CFY-3223, status: Closed'
        self.assertEqual(str(issue), expected_string)

    def test_get_json_issue(self):

        self.assertIsNone(Issue.get_json_issue(None, 'jira_team_name'))

    def test_from_json(self):

        json_issue = {
            'key': u'CFY-3223',
            'fields': {
                'status': {
                    'name': u'Closed'
                }
            }
        }

        expected_issue = Issue(u'CFY-3223', u'Closed')
        self.assertEqual(Issue.from_json(json_issue), expected_issue)

    def test_from_json_no_json(self):

        self.assertIsNone(Issue.from_json(None))

    def test_from_json_missing_parts(self):

        json_issue_no_key = {
            'fields': {
                'status': {
                    'name': u'Closed'
                }
            }
        }

        json_issue_no_status = {
            'key': u'CFY-3223',
            'fields': {}
        }

        self.assertRaises(KeyError, Issue.from_json, json_issue_no_key)
        self.assertRaises(KeyError, Issue.from_json, json_issue_no_status)


class FilterTestCase(unittest.TestCase):

    def test_lt(self):

        filter1 = Filter(1)
        filter2 = Filter(2)

        self.assertLess(filter1, filter2)

    def test_get_filter_class(self):
        self.assertEqual(Filter.get_filter_class('name'), NameFilter)
        self.assertEqual(Filter.get_filter_class('issue'), IssueFilter)
        self.assertRaises(KeyError, Filter.get_filter_class, 'invalid_key')

    @mock.patch('tattle.model.IssueFilter.from_yaml')
    @mock.patch('tattle.model.NameFilter.from_yaml')
    def test_from_yaml(self,
                       mock_name_filter_from_yaml,
                       mock_issue_filter_from_yaml):

        Filter.from_yaml({'type': 'name'})
        self.assertTrue(mock_name_filter_from_yaml.called)
        self.assertFalse(mock_issue_filter_from_yaml.called)

        Filter.from_yaml({'type': 'issue'})
        self.assertTrue(mock_issue_filter_from_yaml.called)


class NameFilterTestCase(unittest.TestCase):

    def test_from_yaml(self):
        yaml_nf = yaml.load('precedence: 1\n'
                            'regular_expressions: [CFY]')

        expected_filter = NameFilter(1, ['CFY'])
        self.assertEqual(NameFilter.from_yaml(yaml_nf), expected_filter)

    def test_legal(self):
        name_filter = NameFilter(1, ['pat'])
        self.assertTrue(name_filter.legal(Organization('pat-1000')))
        self.assertFalse(name_filter.legal((Organization('1000'))))


class IssueFilterTestCase(unittest.TestCase):

    @mock.patch('tattle.model.Transform.from_yaml')
    def test_from_yaml(self, mock_transform_from_yaml):

        yaml_if = yaml.load('precedence: 1\n'
                            'jira_team_name: cloudifysource\n'
                            'jira_statuses:  [Closed, Resolved]\n'
                            'transform:\n'
                            'base_inducer:   CFY-*\d+\n'
                            "edge_case_str:  '-'\n"
                            'edge_from:      CFY\n'
                            'edge_to:        CFY-\n'
                            )
        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        mock_transform_from_yaml.return_value = transform

        expected_filter = IssueFilter(1,
                                      'cloudifysource',
                                      ['Closed', 'Resolved'],
                                      transform
                                      )
        self.assertEqual(IssueFilter.from_yaml(yaml_if), expected_filter)

    def test_legal(self):

        issue_filter = IssueFilter(1,
                                   'cloudifysource',
                                   ['Closed', 'Resolved'],
                                   'transform'
                                   )
        branch = Branch('name', 'repo')
        branch.jira_issue = Issue('CFY-1000', 'Closed')
        self.assertTrue(issue_filter.legal(branch))
        branch.jira_issue = Issue('CFY-1000', 'Resolved')
        self.assertTrue(issue_filter.legal(branch))
        branch.jira_issue = Issue('CFY-1000', 'Open')
        self.assertFalse(issue_filter.legal(branch))


class TransformTestCase(unittest.TestCase):

    def test_from_yaml(self):
        yaml_transform = yaml.load('base:   CFY-*\d+\n'
                                   "if_doesnt_contain:  '-'\n"
                                   'replace_from:      CFY\n'
                                   'replace_to:        CFY-'
                                   )
        expected_transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        self.assertEqual(Transform.from_yaml(yaml_transform),
                         expected_transform
                         )

    def test_transform(self):
        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        src = 'CFY-3223-allow-external-rabbitmq'
        self.assertEqual(transform.transform(src), 'CFY-3223')

    def test_transform_with_if_doesnt_contain(self):

        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        src = 'CFY3223-allow-external-rabbitmq'
        self.assertEqual(transform.transform(src), 'CFY-3223')

    def test_transform_from_and_to_are_the_same(self):

        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY')
        src = 'CFY-3223-allow-external-rabbitmq'
        self.assertEqual(transform.transform(src), 'CFY-3223')

    def test_transform_with_empty_if_doesnt_contain(self):
        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        src = 'CFY-3223-allow-external-rabbitmq'
        self.assertEqual(transform.transform(src), 'CFY-3223')

    def test_transform_base_is_not_a_pattern(self):
        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        src = 'GIVEAWAY'
        self.assertIsNone(transform.transform(src))

    def test_transform_two_base_occurrences(self):
        transform = Transform('CFY-*\d+', '-', 'CFY', 'CFY-')
        src = 'CFY-3223CFY-3223'
        self.assertEqual(transform.transform(src), 'CFY-3223')


class QueryConfigTestCase(unittest.TestCase):

    @mock.patch('tattle.model.os')
    def test_github_credentials_accessing_os_environ(self, mock_os):
        mock_os.environ = {'GITHUB_USER': 'user', 'GITHUB_PASS': 'pass'}
        expected_credentials = ('user', 'pass')
        self.assertEqual(QueryConfig.github_credentials(),
                         expected_credentials)

    def test_from_yaml(self):

        yaml_qc = yaml.load(
            'thread_limit:  120\n'
            'data_type:    branch\n'
            'github_org:   cloudify-cosmo\n'
            'output_path:  /home/avia/tattle/output/report.json\n'
        )

        expected_qc = QueryConfig('branch',
                                  120,
                                  Organization('cloudify-cosmo'),
                                  '/home/avia/tattle/output/report.json'
                                  )
        self.assertEqual(QueryConfig.from_yaml(yaml_qc), expected_qc)


class QueryTestCase(unittest.TestCase):

    def test_get_query_class(self):
        self.assertEqual(Query.get_query_class('branch'), BranchQuery)

    def test_get_query_class_with_invalid_key(self):
        self.assertRaises(KeyError, Query.get_query_class, 'organization')
        self.assertRaises(KeyError, Query.get_query_class, 'repo')
        self.assertRaises(KeyError, Query.get_query_class, 'tag')

    def test_attach_filters(self):
        sorted_filters = [NameFilter(1, None),
                          IssueFilter(2, None, None, None)
                          ]
        unsorted_filters = [IssueFilter(2, None, None, None),
                            NameFilter(1, None)
                            ]
        q = Query(None)
        q.attach_filters(sorted_filters)
        self.assertEqual(q.filters, sorted_filters)
        q.filters = []
        q.attach_filters(unsorted_filters)
        self.assertEqual(q.filters, sorted_filters)


class BranchQueryTestCase(unittest.TestCase):

    @mock.patch('tattle.model.NameFilter.filter')
    @mock.patch('tattle.model.IssueFilter.filter')
    @mock.patch('tattle.model.Branch.update_branches_with_issues')
    @mock.patch('tattle.model.Issue.get_json_issues')
    @mock.patch('tattle.model.Issue.generate_issue_keys')
    def test_filter_with_issue_filter(self,
                                      mock_generate_issue_keys,
                                      mock_get_json_issues,
                                      mock_update_branches_with_issues,
                                      *args
                                      ):
        bq = BranchQuery(QueryConfig(None, None, None, None))
        bq.filters = [IssueFilter(None, None, None, None)]
        bq.filter(None)
        self.assertTrue(mock_generate_issue_keys.called)
        self.assertTrue(mock_get_json_issues.called)
        self.assertTrue(mock_update_branches_with_issues.called)

    @mock.patch('tattle.model.NameFilter.filter')
    @mock.patch('tattle.model.IssueFilter.filter')
    @mock.patch('tattle.model.Branch.update_branches_with_issues')
    @mock.patch('tattle.model.Issue.get_json_issues')
    @mock.patch('tattle.model.Issue.generate_issue_keys')
    def test_filter_without_issue_filter(self,
                                         mock_generate_issue_keys,
                                         mock_get_json_issues,
                                         mock_update_branches_with_issues,
                                         *args
                                         ):
        bq = BranchQuery(QueryConfig(None, None, None, None))
        bq.filters = [NameFilter(None, None)]
        bq.filter(None)
        self.assertFalse(mock_generate_issue_keys.called)
        self.assertFalse(mock_get_json_issues.called)
        self.assertFalse(mock_update_branches_with_issues.called)
