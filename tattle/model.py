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

import itertools
import json
import logging
import math
import os
import posixpath
import re
import sys
import tempfile
from collections import defaultdict
from functools import partial
from multiprocessing.dummy import Pool as ThreadPool

import requests

PROJECT_NAME = 'Tattle'

ITEMS_PER_PAGE = 100
NO_THREAD_LIMIT = sys.maxint

GITHUB_API_URL = 'https://api.github.com/'
ORGS = 'orgs'
REPOS = 'repos'
BRANCHES = 'branches'

PUBLIC_REPOS = 'public_repos'
TOTAL_PRIVATE_REPOS = 'total_private_repos'

JIRA_ISSUE_API_URL_TEMPLATE = 'https://{0}.atlassian.net/rest/api/2/issue/'
JIRA_ISSUE = 'jira_issue'

logger = logging.getLogger('model')
logger.setLevel(logging.DEBUG)
ish = logging.StreamHandler(sys.stdout)
ish.setLevel(logging.INFO)
info_formatter = \
    logging.Formatter('%(asctime)s - %(message)s...', '%Y-%m-%d %H:%M:%S')
ish.setFormatter(info_formatter)
logger.addHandler(ish)


def determine_num_of_threads(thread_limit, num_of_items, per_page=1):

    requested_threads = int(math.ceil(num_of_items / float(per_page)))
    return min(thread_limit, requested_threads)


def create_thread_pool(number_of_threads):
    return ThreadPool(number_of_threads)


def get_json(url, auth=None):

    response = requests.get(url, auth=auth)
    return json.loads(response.text)


def pagination_format(page_number):
    return '?page={0}&per_page={1}'.format(page_number, ITEMS_PER_PAGE)


def generate_github_api_url(request_type,
                            org_name='',
                            repo_name='',
                            branch_name='',
                            page_number=None,
                            ):
    """Return a Github API url based on the given parameters.

    for example, if org_name='cloudify-cosmo', repo_name='tattle',
    branch_name='master', then the response to the Github API url that
    this method returns includes data regarding the branch 'master'
    of the repo 'tattle' of the the organization 'cloudify-cosmo'

    :param request_type: the type of the request, from config.yaml's
                         query_config
    :param org_name: name of a GitHub organization
    :param repo_name: name of a GitHub repository
    :param branch_name: name of a GitHub branch
    :param page_number: the page number to be used in the pagination
                        of the GitHub API
    :return: Github API url
    :rtype: str
    """
    urls = {'organization':    posixpath.join(ORGS,
                                              org_name
                                              ),

            'repos':           posixpath.join(ORGS,
                                              org_name,
                                              REPOS
                                              ) + pagination_format(
                page_number),

            'list_branches':   posixpath.join(REPOS,
                                              org_name,
                                              repo_name,
                                              BRANCHES
                                              ),

            'detailed_branch': posixpath.join(REPOS,
                                              org_name,
                                              repo_name,
                                              BRANCHES,
                                              branch_name)
            }

    return posixpath.join(GITHUB_API_URL,
                          urls[request_type])


class GitHubObject(object):
    """ Parent class for all classes representing GitHub objects.

    Contains methods shared by all the GitHub objects,
    such as rich comparison methods.
    """
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.name < other.name


class Organization(GitHubObject):
    """ Represents a GitHub organization
    """
    def __init__(self, name):
        super(Organization, self).__init__(name)

    def __str__(self):
        return self.name

    @staticmethod
    def get_num_of_repos(org):
        """ Returns the number of repos of the `org` GitHub organization.

        The number of repos includes the number of the private repos.
        This method interacts with the GitHub API in order to retrieve
        information about the `org` organization.
        The numbers of the public and private repos are extracted from this
        information, and added together as the method's return value

        :param org: GitHub organization
        :return: the number of repos of the specified organization
        :rtype: int
        """

        url = generate_github_api_url('organization', org_name=org.name)

        json_org = get_json(url, auth=QueryConfig.github_credentials())

        return (json_org.get(PUBLIC_REPOS, 0) +
                json_org.get(TOTAL_PRIVATE_REPOS, 0))


class Repo(GitHubObject):

    def __init__(self, name, org=None):
        super(Repo, self).__init__(name)
        self.organization = org

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Repo(name={0},org={1})'.format(self.name,
                                               self.organization)

    @classmethod
    def from_json(cls, json_repo):
        name = json_repo['name']
        organization = Organization(json_repo['owner']['login'])
        return cls(name, organization)

    @classmethod
    def get_repos(cls, org, thread_limit=NO_THREAD_LIMIT):
        logger.info('retrieving github repositories for the {0} organization'
                    .format(org))

        num_of_repos = Organization.get_num_of_repos(org)
        num_of_threads = determine_num_of_threads(thread_limit,
                                                  num_of_repos,
                                                  per_page=ITEMS_PER_PAGE)
        pool = create_thread_pool(num_of_threads)

        json_repos = pool.map(partial(cls.get_json_repos, org=org),
                              range(1, num_of_threads + 1)
                              )
        repos = []
        for list_of_json_repos in json_repos:
            for json_repo in list_of_json_repos:
                repos.append(cls.from_json(json_repo))

        return repos

    @staticmethod
    def get_json_repos(page_number, org):

        url = generate_github_api_url('repos',
                                      org_name=org.name,
                                      page_number=page_number,
                                      )

        return get_json(url, auth=QueryConfig.github_credentials())


class Branch(GitHubObject):

    def __init__(self,
                 name,
                 repo,
                 jira_issue=None,
                 committer_email=None):
        super(Branch, self).__init__(name)
        self.repo = repo
        self.jira_issue = jira_issue
        self.committer_email = committer_email

    def __str__(self):
        return self.name

    @classmethod
    def from_json(cls, json_branch):

        name = json_branch['name']
        (repo_name, organization) = cls.extract_repo_data(
            json_branch['commit']['url'])
        repo = Repo(repo_name, org=organization)

        return cls(name, repo)

    @staticmethod
    def extract_repo_data(branch_url):
        url_regex = re.compile(
            r'https://api.github.com/repos/(.*)/(.*)/commits/(.*)')
        groups = url_regex.findall(branch_url)
        name = groups[0][1]
        organization = Organization(groups[0][0])
        return name, organization

    @classmethod
    def get_org_branches(cls, repos, org, thread_limit=NO_THREAD_LIMIT):
        logger.info('retrieving basic github branch info '
                    'for the {0} organization'
                    .format(org))
        num_of_threads = determine_num_of_threads(thread_limit, len(repos))
        pool = create_thread_pool(num_of_threads)

        json_branches_lists = pool.map(cls.get_json_branches, repos)

        # pool.map returned a list of lists of json-formatted branches.
        # below we convert it to a list of Branch objects:
        branches = []
        for json_branches_list in json_branches_lists:
            branches.extend([cls.from_json(json_branch)
                             for json_branch in json_branches_list])
        return sorted(branches)

    @staticmethod
    def get_json_branches(repo):

        url = generate_github_api_url('list_branches',
                                      org_name=repo.organization.name,
                                      repo_name=repo.name)

        return get_json(url, auth=QueryConfig.github_credentials())

    @staticmethod
    def update_branches_with_issues(branches, issues):
        for branch, issue in itertools.izip(branches, issues):
            branch.jira_issue = issue

    @classmethod
    def get_details(cls, branches, thread_limit):
        if branches:
            logger.info('retrieving detailed github branch info '
                        'for the {0} organization'
                        .format(branches[0].repo.organization.name))

        num_of_threads = determine_num_of_threads(thread_limit, len(branches))
        pool = create_thread_pool(num_of_threads)

        return pool.map(cls.fetch_details, branches)

    @staticmethod
    def fetch_details(branch):

        url = generate_github_api_url('detailed_branch',
                                      org_name=branch.repo.organization.name,
                                      repo_name=branch.repo.name,
                                      branch_name=branch.name
                                      )

        return get_json(url, auth=QueryConfig.github_credentials())

    @staticmethod
    def update_details(branch, details):
        branch.committer_email = details['commit']['commit']['author']['email']


class Issue(object):

    STATUSES = [u'Assigned', u'Build' u'Broken', u'Building', u'Closed',
                u'Done', u'Info Needed', u'In Progress', u'Open',
                u'Pending', u'Pull Request', u'Reopened', u'Resolved',
                u'Stopped', u'To Do'
                ]

    def __init__(self, key, status):

        self.key = key
        self.status = status

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'key: {0}, status: {1}'.format(self.key, self.status)

    @staticmethod
    def generate_issue_keys(items, transform):

        names = [item.name for item in items]
        return [transform.transform(name) for name in names]

    @classmethod
    def get_json_issues(cls, keys, jira_team_name,
                        thread_limit=NO_THREAD_LIMIT):

        number_of_threads = determine_num_of_threads(thread_limit, len(keys))
        pool = create_thread_pool(number_of_threads)

        return pool.map(
            partial(cls.get_json_issue, jira_team_name=jira_team_name),
            keys
        )

    @staticmethod
    def get_json_issue(key, jira_team_name):

        if key is None:  # because of CFY-GIVEAWAY
            return key
        url = posixpath.join(JIRA_ISSUE_API_URL_TEMPLATE
                             .format(jira_team_name),
                             key,
                             '?fields=status'
                             )
        return get_json(url)

    @classmethod
    def from_json(cls, json_issue):
        if json_issue is None:
            return None
        try:
            key = json_issue['key']
            status = json_issue['fields']['status']['name']
        except KeyError:
            raise KeyError('This json does not represent a valid JIRA issue')
        return cls(key, status)


class Filter(object):

    PRECEDENCE = 'precedence'

    def __init__(self, precedence):
        self.precedence = precedence

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.precedence < other.precedence

    @staticmethod
    def get_filter_class(filter_class):

        filters_dict = {'name': NameFilter, 'issue': IssueFilter}
        return filters_dict[filter_class]

    @classmethod
    def from_yaml(cls, yaml_filter):
        filter_class = cls.get_filter_class(yaml_filter['type'])
        return filter_class.from_yaml(yaml_filter)


class NameFilter(Filter):

    REGEXES = 'regular_expressions'

    def __init__(self, precedence, regexes):
        super(NameFilter, self).__init__(precedence)
        self.regexes = regexes

    @classmethod
    def from_yaml(cls, yaml_nf):

        precedence = yaml_nf.get(cls.PRECEDENCE, sys.maxint)
        regexes = yaml_nf.get(cls.REGEXES, list())
        return cls(precedence, regexes)

    def filter(self, items):
        return filter(self.legal, items)

    def legal(self, item):
        for regex in self.regexes:
            if re.search(regex, item.name):
                return True
        return False


class IssueFilter(Filter):

    JIRA_TEAM_NAME = 'jira_team_name'
    JIRA_STATUSES = 'jira_statuses'
    TRANSFORM = 'transform'

    def __init__(self,
                 precedence,
                 jira_team_name,
                 jira_statuses,
                 transform):
        super(IssueFilter, self).__init__(precedence)
        self.jira_team_name = jira_team_name
        self.jira_statuses = jira_statuses
        self.transform = transform

    @classmethod
    def from_yaml(cls, yaml_if):
        precedence = yaml_if.get(cls.PRECEDENCE, sys.maxint)
        jira_team_name = yaml_if.get(cls.JIRA_TEAM_NAME)
        jira_statuses = yaml_if.get(cls.JIRA_STATUSES, Issue.STATUSES)

        yaml_transform = yaml_if.get(cls.TRANSFORM, None)
        transform = Transform.from_yaml(yaml_transform)

        return cls(precedence, jira_team_name, jira_statuses, transform)

    def filter(self, items):
        return filter(self.legal, items)

    def legal(self, item):
        if item.jira_issue is None:
            return False
        return item.jira_issue.status in self.jira_statuses


class Transform(object):

    BASE = 'base'
    IF_DOESNT_CONTAIN = 'if_doesnt_contain'
    REPLACE_FROM = 'replace_from'
    REPLACE_TO = 'replace_to'

    def __init__(self, base, if_doesnt_contain, replace_from, replace_to):
        self.base = base
        self.if_doesnt_contain = if_doesnt_contain
        self.replace_from = replace_from
        self.replace_to = replace_to

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    @classmethod
    def from_yaml(cls, yaml_tf):

        if yaml_tf is None:
            return None

        base = yaml_tf.get(cls.BASE)
        if_doesnt_contain = yaml_tf.get(cls.IF_DOESNT_CONTAIN, '')
        replace_from = yaml_tf.get(cls.REPLACE_FROM)
        replace_to = yaml_tf.get(cls.REPLACE_TO)

        return cls(base, if_doesnt_contain, replace_from, replace_to)

    def transform(self, src):

        base = re.search(self.base, src)
        if base is not None:
            group = base.group()
            if self.if_doesnt_contain == '':
                return group
            if self.if_doesnt_contain not in group:
                return group.replace(self.replace_from,
                                     self.replace_to)
            else:
                return group
        else:
            return None


class QueryConfig(object):

    DATA_TYPE = 'data_type'
    THREAD_LIMIT = 'thread_limit'
    GITHUB_ORG = 'github_org'
    OUTPUT_PATH = 'output_path'
    DEFAULT_OUTPUT_FILE_NAME = 'report.json'
    DEFAULT_OUTPUT_RELATIVE_PATH = os.path.join(PROJECT_NAME,
                                                DEFAULT_OUTPUT_FILE_NAME)
    DEFAULT_OUTPUT_PATH = os.path.join(tempfile.gettempdir(),
                                       DEFAULT_OUTPUT_RELATIVE_PATH)

    @staticmethod
    def github_credentials():
        return (os.environ['GITHUB_USER'],
                os.environ['GITHUB_PASS'])

    def __init__(self,
                 data_type,
                 thread_limit,
                 github_org,
                 output_path):

        self.data_type = data_type
        self.thread_limit = thread_limit
        self.github_org = github_org
        self.output_path = output_path

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    @classmethod
    def from_yaml(cls, yaml_qc):

        data_type = yaml_qc.get(cls.DATA_TYPE)
        thread_limit = yaml_qc.get(cls.THREAD_LIMIT, NO_THREAD_LIMIT)
        github_org = yaml_qc.get(cls.GITHUB_ORG)
        output_path = yaml_qc.get(cls.OUTPUT_PATH, cls.DEFAULT_OUTPUT_PATH)

        return cls(data_type,
                   thread_limit,
                   Organization(github_org),
                   output_path)


class Query(object):

    def __init__(self, config):

        self.config = config
        self.filters = []
        self.result = None

    @staticmethod
    def get_query_class(query_class_str):

        query_dict = {'branch': BranchQuery}
        return query_dict[query_class_str]

    @classmethod
    def from_config(cls, config):

        query_class = cls.get_query_class(config.data_type)
        return query_class(config)

    def attach_filters(self, filters):
        """
        Sorts `filters` by precedence,
        and then by their relative order in config.yaml
        :param filters: a list of Filter-subclasses objects
        """
        precedence_dict = defaultdict(list)

        for f in filters:
            precedence_dict[f.precedence].append(f)

        for key in sorted(precedence_dict.keys()):
            self.filters.extend(precedence_dict[key])

    def output(self):

        output_path = self.config.output_path
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        file_logger = logging.getLogger('model')
        fh = logging.FileHandler(self.config.output_path)
        fh.setLevel(logging.INFO)
        file_logger.addHandler(fh)
        file_logger.log(logging.INFO, json.dumps(self.result,
                                                 default=lambda x: x.__dict__)
                        )


class BranchQuery(Query):

    def __init__(self, config):
        super(BranchQuery, self).__init__(config)
        self.issues = None

    def query(self):

        repos = Repo.get_repos(self.config.github_org,
                               self.config.thread_limit)

        branches = Branch.get_org_branches(
            repos,
            self.config.github_org,
            thread_limit=self.config.thread_limit
            )

        query_branches = self.filter(branches)
        details = Branch.get_details(query_branches,
                                     self.config.thread_limit)

        for branch, branch_details in itertools.izip(query_branches, details):
            Branch.update_details(branch, branch_details)

        self.result = query_branches

    def filter(self, branches):
        for f in self.filters:
            if isinstance(f, IssueFilter) and not self.issues:
                keys = Issue.generate_issue_keys(branches, f.transform)
                json_issues = \
                    Issue.get_json_issues(
                        keys,
                        f.jira_team_name,
                        thread_limit=self.config.thread_limit)
                self.issues = [Issue.from_json(j_issue)
                               for j_issue in json_issues]
                Branch.update_branches_with_issues(branches, self.issues)
            branches = f.filter(branches)
        return branches
