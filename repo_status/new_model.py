import itertools
import json
import logging
import os
import posixpath
import re
import requests
import sys
import tempfile


from collections import defaultdict
from multiprocessing.dummy import Pool as ThreadPool

PROJECT_NAME = 'Tattle'

GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
REPOS_PER_PAGE = 100

GITHUB_API_URL = 'https://api.github.com/'
ORGS = 'orgs'
REPOS = 'repos'
REPO = 'repo'
PUBLIC_REPOS = 'public_repos'
TOTAL_PRIVATE_REPOS = 'total_private_repos'
BRANCHES = 'branches'

JIRA_ISSUE = 'jira_issue'

logger = logging.getLogger('model')
logger.setLevel(logging.DEBUG)
ish = logging.StreamHandler(sys.stdout)
ish.setLevel(logging.INFO)
info_formatter = logging.Formatter('%(asctime)s - %(message)s...', '%Y-%m-%d %H:%M:%S')
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


class Branch(GitHubObject):

    def __init__(self,
                 name,
                 repo,
                 committer_email,
                 jira_issue=None,
                 ):
        super(Branch, self).__init__(name)
        self.repo = repo
        self.jira_issue = jira_issue
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
    NO_THREAD_LIMIT = -1
    GITHUB_ORG_NAME = 'github_org_name'
    OUTPUT_PATH = 'output_path'
    DEFAULT_OUTPUT_FILE_NAME = 'report.json'
    DEFAULT_OUTPUT_RELATIVE_PATH = os.path.join(PROJECT_NAME,
                                                DEFAULT_OUTPUT_FILE_NAME)
    DEFAULT_OUTPUT_PATH = os.path.join(tempfile.gettempdir(),
                                       DEFAULT_OUTPUT_RELATIVE_PATH)

    def __init__(self,
                 data_type,
                 max_threads,
                 github_org_name,
                 output_path):

        self.data_type = data_type
        self.max_threads = max_threads
        self.github_org_name = github_org_name
        self.output_path = output_path

    @classmethod
    def from_yaml(cls, yaml_qc):

        data_type = yaml_qc.get(cls.DATA_TYPE)
        max_threads = yaml_qc.get(cls.MAX_THREADS, cls.NO_THREAD_LIMIT)
        github_org_name = yaml_qc.get(cls.GITHUB_ORG_NAME)
        output_path = yaml_qc.get(cls.OUTPUT_PATH, cls.DEFAULT_OUTPUT_PATH)

        return cls(data_type, max_threads, github_org_name, output_path)


class Issue(object):

    STATUSES = ['Assigned', 'Build' 'Broken', 'Building', 'Closed', 'Done', 'Info Needed',
                'In Progress', 'Open', 'Pending', 'Pull Request', 'Reopened', 'Resolved',
                'Stopped', 'To Do']


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
        :param filters: a list of Filter subclasses
        :return: the filters sorted by precedence,
        and then by their relative order in the config.yaml file
        """
        self.filters = []
        precedence_dict = defaultdict([])

        for f in filters:
            precedence_dict[f.precedence].append(f)

        for key in sorted(precedence_dict.keys()):
            self.filters.extend(precedence_dict[key])

    def determine_number_of_threads(self, items):

        if self.config.max_threads == QueryConfig.NO_THREAD_LIMIT:
            return len(items)
        return min(self.config.max_threads, len(items))

    def get_num_of_repos(self):

        url = posixpath.join(GITHUB_API_URL,
                             ORGS,
                             self.config.github_org_name
                             )
        r = requests.get(url,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS]))
        json_org = json.loads(r.text)

        return json_org[PUBLIC_REPOS] + json_org[TOTAL_PRIVATE_REPOS]

    def get_json_repos(self, page_number):

        pagination_parameters = '?page={0}&per_page={1}' \
            .format(page_number, REPOS_PER_PAGE)

        url = posixpath.join(GITHUB_API_URL,
                             ORGS,
                             self.config.github_org_name,
                             REPOS + pagination_parameters,
                             )
        response = requests.get(url, auth=(os.environ[GITHUB_USER],
                                           os.environ[GITHUB_PASS]))
        return json.loads(response.text)

    def get_repos(self):
        logger.info('retrieving github repositories for the {0} organization'
                    .format(self.config.github_org_name))

        num_of_repos = self.get_num_of_repos()
        num_of_threads = self.determine_number_of_threads(num_of_repos /
                                                          REPOS_PER_PAGE+1)
        pool = ThreadPool(num_of_threads)
        json_repos = pool.map(self.get_json_repos, range(1, num_of_threads+1))

        repos = []
        for list_of_json_repos in json_repos:
            for json_repo in list_of_json_repos:
                repos.append(Repo.from_json(json_repo))

        return repos


class BranchQuery(Query):

    def __init__(self, config, repos):
        super(BranchQuery, self).__init__(config)

    def query(self):

        repos = self.get_repos
        branches = self.get_org_branches(repos)
        query_branches = self.filter(branches)

    def filter(self, branches):
        pass

    def get_org_branches(self, repos):
        logger.info('retrieving basic github branch info '
                    'for the {0} organization'
                    .format(self.config.github_org_name))
        num_of_threads = self.determine_number_of_threads(len(repos))
        pool = ThreadPool(num_of_threads)
        lists_of_branches = pool.map(self.get_repo_branches, repos)
        return list(itertools.chain.from_iterable(lists_of_branches))

    def get_repo_branches(self, repo):

        json_branches = self.get_json_branches(repo.name)
        branch_list = [Branch.from_json(jb) for jb in json_branches]

        return sorted(branch_list)

    def get_json_branches(self, repo_name):

        url = posixpath.join(GITHUB_API_URL,
                             REPOS,
                             self.config.github_org_name,
                             repo_name,
                             BRANCHES
                             )
        r = requests.get(url, auth=(os.environ[GITHUB_USER],
                                    os.environ[GITHUB_PASS]))
        return json.loads(r.text)
