import itertools
import json
import logging
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

GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
REPOS_PER_PAGE = 100
NO_THREAD_LIMIT = sys.maxint

GITHUB_API_URL = 'https://api.github.com/'
ORGS = 'orgs'
REPOS = 'repos'
REPO = 'repo'
PUBLIC_REPOS = 'public_repos'
TOTAL_PRIVATE_REPOS = 'total_private_repos'
BRANCHES = 'branches'

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


class GitHubObject(object):

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

    def __init__(self, name):
        super(Organization, self).__init__(name)

    def __str__(self):
        return self.name

    @staticmethod
    def get_num_of_repos(org):

        url = posixpath.join(GITHUB_API_URL,
                             ORGS,
                             org.name
                             )
        r = requests.get(url,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS]))
        json_org = json.loads(r.text)

        return json_org[PUBLIC_REPOS] + json_org[TOTAL_PRIVATE_REPOS]


class Repo(GitHubObject):

    def __init__(self, name):
        super(Repo, self).__init__(name)

    def __str__(self):
        return 'Repository: {0}'.format(self.name)

    def __repr__(self):
        return 'Repo(name={0})'.format(self.name)

    @classmethod
    def from_json(cls, json_repo):
        return cls(json_repo['name'])

    @classmethod
    def get_repos(cls, org, max_threads=NO_THREAD_LIMIT):
        logger.info('retrieving github repositories for the {0} organization'
                    .format(org))
        num_of_repos = Organization.get_num_of_repos(org)
        num_of_threads = min(num_of_repos / REPOS_PER_PAGE+1, max_threads)
        pool = ThreadPool(num_of_threads)

        json_repos = pool.map(partial(cls.get_json_repos, org=org),
                              range(1, num_of_threads+1)
                              )
        repos = []
        for list_of_json_repos in json_repos:
            for json_repo in list_of_json_repos:
                repos.append(cls.from_json(json_repo))

        return repos

    @staticmethod
    def get_json_repos(page_number, org):

        pagination_parameters = '?page={0}&per_page={1}' \
            .format(page_number, REPOS_PER_PAGE)

        url = posixpath.join(GITHUB_API_URL,
                             ORGS,
                             org.name,
                             REPOS + pagination_parameters,
                             )
        response = requests.get(url, auth=(os.environ[GITHUB_USER],
                                           os.environ[GITHUB_PASS]))
        return json.loads(response.text)


class Branch(GitHubObject):

    def __init__(self,
                 name,
                 repo,
                 committer_email
                 ):
        super(Branch, self).__init__(name)
        self.repo = repo
        self.jira_issue = None
        self.committer_email = committer_email

    @classmethod
    def from_json(cls, json_branch):

        repo = None if json_branch[REPO] is None \
            else Repo(json_branch[REPO]['name'])

        committer_email = json_branch['committer_email']

        # jira_issue = None if json_branch[JIRA_ISSUE] is None \
        #     else Issue(json_branch[JIRA_ISSUE]['key'],
        #                json_branch[JIRA_ISSUE]['status'])

        return cls(json_branch['name'],
                   repo,
                   committer_email
                   # jira_issue=jira_issue,
                   )

    def __str__(self):
        issue = '' if self.jira_issue is None else str(self.jira_issue)

        return 'Branch name: {0}\n{1}Last committer: {2}\n'. \
            format(self.name, issue, self.committer_email.encode('utf-8'))

    @classmethod
    def get_org_branches(cls, repos, org, max_threads=NO_THREAD_LIMIT):
        logger.info('retrieving basic github branch info '
                    'for the {0} organization'
                    .format(org))
        num_of_threads = min(max_threads, len(repos))
        pool = ThreadPool(num_of_threads)
        json_branches_lists = pool.map(partial(cls.get_json_branches,
                                               org=org),
                                       repos
                                       )
        # pool.map returned a list of lists of json-formatted branches.
        # below we convert it to a list of Branch objects:
        branches = []
        for json_branches_list in json_branches_lists:
            branches.extend([cls.from_json(json_branch)
                             for json_branch in json_branches_list])
        return sorted(branches)

    @staticmethod
    def get_json_branches(repo_name, org):

        url = posixpath.join(GITHUB_API_URL,
                             REPOS,
                             org.name,
                             repo_name,
                             BRANCHES
                             )
        r = requests.get(url, auth=(os.environ[GITHUB_USER],
                                    os.environ[GITHUB_PASS]))
        return json.loads(r.text)

    @staticmethod
    def update_branches_with_issues(branches, issues):
        for branch, issue in itertools.izip(branches, issues):
            branch.jira_issue = issue


class Precedence(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.name]

    def __set__(self, instance, value):

        if not isinstance(value, int) or value <= 0:
            raise TypeError('a precedence is a positive integer')

        instance.__dict__[self.name] = value


class Filter(object):

    PRECEDENCE = 'precedence'

    precedence = Precedence(PRECEDENCE)

    def __init__(self, precedence):
        # TODO make precedence take only positive numbers (not even zero).
        # Do it with a descriptor class, like the old PerformanceTime
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
        filter_class = cls.get_filter_class(yaml_filter.type)
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
        transform = yaml_if.get(cls.TRANSFORM, None)

        return cls(precedence, jira_team_name, jira_statuses, transform)

    def filter(self, items):
        return filter(self.legal, items)

    def legal(self, issue):
        return issue.status in self.jira_statuses


class QueryConfig(object):

    DATA_TYPE = 'data_type'
    MAX_THREADS = 'max_threads'
    GITHUB_ORG = 'github_org'
    OUTPUT_PATH = 'output_path'
    DEFAULT_OUTPUT_FILE_NAME = 'report.json'
    DEFAULT_OUTPUT_RELATIVE_PATH = os.path.join(PROJECT_NAME,
                                                DEFAULT_OUTPUT_FILE_NAME)
    DEFAULT_OUTPUT_PATH = os.path.join(tempfile.gettempdir(),
                                       DEFAULT_OUTPUT_RELATIVE_PATH)

    def __init__(self,
                 data_type,
                 max_threads,
                 github_org,
                 output_path):

        self.data_type = data_type
        self.max_threads = max_threads
        self.github_org = github_org
        self.output_path = output_path

    @classmethod
    def from_yaml(cls, yaml_qc):

        data_type = yaml_qc.get(cls.DATA_TYPE)
        max_threads = yaml_qc.get(cls.MAX_THREADS, NO_THREAD_LIMIT)
        github_org = yaml_qc.get(cls.GITHUB_ORG)
        output_path = yaml_qc.get(cls.OUTPUT_PATH, cls.DEFAULT_OUTPUT_PATH)

        return cls(data_type,
                   max_threads,
                   Organization(github_org),
                   output_path)


class Query(object):

    def __init__(self, config):

        self.config = config
        self.filters = {}

    @staticmethod
    def get_query_class(query_class):

        query_dict = {'branch': BranchQuery}
        return query_dict[query_class]

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
        self.filters = []
        precedence_dict = defaultdict([])

        for f in filters:
            precedence_dict[f.precedence].append(f)

        for key in sorted(precedence_dict.keys()):
            self.filters.extend(precedence_dict[key])


class BranchQuery(Query):

    def __init__(self, config):
        super(BranchQuery, self).__init__(config)
        self.issues = None

    def query(self):

        repos = Repo.get_repos
        branches = Branch.get_org_branches(repos,
                                           self.config.github_org,
                                           max_threads=self.config.max_threads
                                           )
        query_branches = self.filter(branches)

    def filter(self, branches):
        for f in self.filters:
            if isinstance(f, IssueFilter) and not self.issues:
                keys = Issue.generate_issue_keys(branches, f.transform)
                json_issues = \
                    Issue.get_json_issues(keys,
                                          f.jira_team_name,
                                          max_threads=self.config.max_threads)
                issues = [Issue.from_json(j_issue) for j_issue in json_issues]
                Branch.update_branches_with_issues(branches, self.issues)
            branches = f.filter(branches)
        return branches


class IssueStatus(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.name]

    def __set__(self, instance, value):

        if not isinstance(value, str):
            raise TypeError('a JIRA issue status is expected to be a string')

        if value not in Issue.STATUSES:
            raise ValueError('Not a defined JIRA issue status')

        instance.__dict__[self.name] = value


class Issue(object):

    status = IssueStatus('status')

    # TODO genetare the status list according to the team's jira status list.
    STATUSES = ['Assigned', 'Build' 'Broken', 'Building', 'Closed', 'Done',
                'Info Needed', 'In Progress', 'Open', 'Pending',
                'Pull Request', 'Reopened', 'Resolved', 'Stopped', 'To Do'
                ]

    def __init__(self, key, status):

        # TODO think if we need an attribute 'related object' here
        self.key = key
        self.status = status
        # TODO enforce `status` to be one of Issue.STATUSES

    @staticmethod
    def generate_issue_keys(items, transform):

        names = [item.name for item in items]
        return [transform.transform(name) for name in names]

    @classmethod
    def get_json_issues(cls, keys, jira_team_name,
                        max_threads=NO_THREAD_LIMIT):

        number_of_threads = min(max_threads, len(keys))
        pool = ThreadPool(number_of_threads)
        return pool.map(
            partial(cls.get_json_issue, jira_team_name=jira_team_name),
            keys
            )

    @staticmethod
    def get_json_issue(key, jira_team_name):
        # TODO understand if the comment below is needed
        # if key is None:  # because of CFY-GIVEAWAY
        #     return key
        url = posixpath.join(JIRA_ISSUE_API_URL_TEMPLATE
                             .format(jira_team_name),
                             key,
                             '?fields=status'
                             )
        response = requests.get(url)
        return json.loads(response.text)

    @classmethod
    def from_json(cls, json_issue):
        if json_issue is None:
            return None
        try:
            key = json_issue['key']
            status = json_issue
        except KeyError:
            raise KeyError('This json does not represent a valid JIRA issue')
        return cls(key, status)
