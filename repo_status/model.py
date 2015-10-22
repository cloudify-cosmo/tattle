import abc
import itertools
import json
import os
import re
import requests
import time

from multiprocessing.dummy import Pool as ThreadPool

BRANCHES = 'branches'
REPOS = 'repos'
ORGS = 'orgs'

CONTAINING_REPO = 'containing_repo'

GITHUB_API_URL = 'https://api.github.com/'
CLOUDIFY_COSMO = 'cloudify-cosmo'
PUBLIC_REPOS = 'public_repos'
TOTAL_PRIVATE_REPOS = 'total_private_repos'
USERNAME = 'AviaE'
PASSWORD = 'A1b2Y8z9'
os.environ['GITHUB_USER'] = 'AviaE'  # remove this later
os.environ['GITHUB_PASS'] = 'A1b2Y8z9'  # remove this later
GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'


class Repo(object):

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

    def __str__(self):
        return 'Repository: {0}'.format(self.name)

    def __repr__(self):
        return 'Repo(name={0})'.format(self.name)


class Branch(object):

    def __init__(self,
                 name,
                 containing_repo,
                 jira_issue=None,
                 last_committer=''
                 ):
        self.name = name
        self.containing_repo = containing_repo
        self.jira_issue = jira_issue
        self.committer_email = last_committer

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        issue = '' if self.jira_issue is None else str(self.jira_issue)

        return 'Branch name: {0}\n{1}Last committer: {2}\n'. \
            format(self.name, issue, self.committer_email.encode('utf-8'))


class Issue(object):

    JIRA_API_URL = 'https://cloudifysource.atlassian.net/rest/api/2/issue/'
    JIRA_STR_TEMPLATE = u'JIRA status: {0}\n'
    STATUS_CLOSED = u'Closed'
    STATUS_RESOLVED = u'Resolved'

    def __init__(self, key, status):
        self.key = key
        self.status = status

    def __hash__(self):
        return hash((self.key, self.status))

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):

        return self.JIRA_STR_TEMPLATE\
            .format(self.status)

    @staticmethod
    def extract_issue_key(branch):

        match_object = re.search('CFY-*\d+', branch.name)
        if match_object is not None:
            group = match_object.group()
            if '-' not in group:
                return group.replace('CFY', 'CFY-')
            else:
                return group
        else:
            return None


class QueryConfig(object):

    NO_THREAD_LIMIT = -1

    def __init__(self,
                 resources_path,
                 max_threads=NO_THREAD_LIMIT,
                 org_name=CLOUDIFY_COSMO):

        self.resources_path = resources_path
        self.filename = ''
        self.org_name = org_name
        self.max_threads = max_threads

    def get_cache_path(self):

        return os.path.join(self.resources_path, self.filename)


class QueryPerformance(object):

    def __init__(self):

        self.start = 0
        self.repos_start = 0
        self.repos_end = 0
        self.basic_branches_start = 0
        self.basic_branches_end = 0
        self.issues_start = 0
        self.issues_end = 0
        self.detailed_branches_start = 0
        self.detailed_branches_end = 0
        self.end = 0

    def total(self):
        return (self.end - self.start) * 1000

    def repos(self):
        return (self.repos_end - self.repos_start) * 1000

    def basic_branches(self):
        return (self.basic_branches_end - self.basic_branches_start) * 1000

    def issues(self):
        return (self.issues_end - self.issues_start) * 1000

    def detailed_branches(self):
        return (self.detailed_branches_end - self.detailed_branches_start) * 1000


class BranchQueryAbstract(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def filter_branches(self, branches):
        pass


class BranchQuery(BranchQueryAbstract):

    DESCRIPTION = None

    ACTION_PERFORMANCE_TEMPLATE = '\naction:\n{0}\n'
    REPOS_PERFORMANCE_TEMPLATE = 'getting the repos: {0}ms'
    BASIC_BRANCH_INFO_PERFORMANCE_TEMPLATE = 'getting basic branch info: {0}ms'
    ISSUES_PERFORMANCE_TEMPLATE = 'getting the issues: {0}ms'
    DETAILED_BRANCH_INFO_PERFORMANCE_TEMPLATE = 'getting detailed branch info: {0}ms'
    TOTAL_PERFORMANCE_TEMPLATE = 'total time: {0}ms'

    def filter_branches(self, branches):
        pass

    def __init__(self, query_config):
        self.config = query_config
        self.performance = QueryPerformance()

    def update_cache(self, query_branches):
        self.store_branches(query_branches)

    def output(self, branches):

        cur_repo_name = None

        for b in branches:
            running_repo_name = b.containing_repo.name
            if cur_repo_name != running_repo_name:
                if cur_repo_name is not None:
                    print ''
                cur_repo_name = running_repo_name
                print '*' * (len(str(b.containing_repo)))
                print str(b.containing_repo)
                print '*' * (len(str(b.containing_repo)))

            print b

    def print_performance(self):

        print self.ACTION_PERFORMANCE_TEMPLATE\
            .format(self.DESCRIPTION)
        print self.REPOS_PERFORMANCE_TEMPLATE\
            .format(self.performance.repos())
        print self.BASIC_BRANCH_INFO_PERFORMANCE_TEMPLATE\
            .format(self.performance.basic_branches())
        print self.ISSUES_PERFORMANCE_TEMPLATE\
            .format(self.performance.issues())
        print self.DETAILED_BRANCH_INFO_PERFORMANCE_TEMPLATE\
            .format(self.performance.detailed_branches())
        print self.TOTAL_PERFORMANCE_TEMPLATE\
            .format(self.performance.total())

    def determine_number_of_threads(self, number_of_calls):
        max_number_of_threads = self.config.max_threads
        if max_number_of_threads == QueryConfig.NO_THREAD_LIMIT:
            return number_of_calls
        else:
            return min(number_of_calls, max_number_of_threads)

    def get_num_of_repos(self):

        org_name = self.config.org_name

        full_address = os.path.join(GITHUB_API_URL,
                                    ORGS,
                                    org_name)
        r = requests.get(full_address,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS]))
        dr = json.loads(r.text)

        return dr[PUBLIC_REPOS] + dr[TOTAL_PRIVATE_REPOS]

    def get_repo(self, repo_num):
        pagination_parameters = '?page={0}&per_page=1'.format(repo_num)
        full_address = os.path.join(GITHUB_API_URL,
                                    ORGS,
                                    self.config.org_name,
                                    REPOS + pagination_parameters,
                                    )
        response = requests.get(full_address,
                                auth=(os.environ[GITHUB_USER],
                                      os.environ[GITHUB_PASS])
                                )

        repo_dict = json.loads(response.text)
        repo = Repo(repo_dict[0]['name'])
        return repo

    def get_repos(self):
        self.performance.repos_start = time.time()

        num_of_repos = self.get_num_of_repos()
        num_of_threads = self.determine_number_of_threads(num_of_repos)

        pool = ThreadPool(num_of_threads)
        repos = pool.map(self.get_repo, range(1, num_of_threads+1))

        self.performance.repos_end = time.time()

        return repos

    def get_json_branches(self, repo_name, org_name=CLOUDIFY_COSMO):

        full_address = os.path.join(GITHUB_API_URL,
                                    REPOS,
                                    org_name,
                                    repo_name,
                                    BRANCHES)
        r = requests.get(full_address,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS])
                         )
        return r.text

    def parse_json_branches(self, json_branches, repo_object):
        detailed_list_of_branches = json.loads(json_branches)
        list_of_branch_objects = [Branch(db['name'], repo_object)
                                  for db in detailed_list_of_branches]

        return list_of_branch_objects

    def get_branches(self, repo_object, org_name=CLOUDIFY_COSMO):

        json_branches = self.get_json_branches(repo_object.name, org_name)
        branch_list = self.parse_json_branches(json_branches, repo_object)

        return sorted(branch_list)

    def get_org_branches(self):

        repos = self.get_repos()

        self.performance.basic_branches_start = time.time()
        num_of_threads = self.determine_number_of_threads(len(repos))
        pool = ThreadPool(num_of_threads)

        branches_lists = pool.map(self.get_branches, repos)
        self.performance.basic_branches_end = time.time()
        return list(itertools.chain.from_iterable(branches_lists))

    def load_branches(self):

        json_filepath = self.config.get_cache_path()
        branches = []
        with open(json_filepath, 'r') as branches_file:
            json_branches = json.load(branches_file)
            for json_branch in json_branches[BRANCHES]:

                repo = None if json_branch[CONTAINING_REPO] is None \
                    else Repo(json_branch[CONTAINING_REPO]
                                         ['name'])
                jira_issue = None if json_branch['jira_issue'] is None \
                    else Issue(json_branch['jira_issue']['key'],
                               json_branch['jira_issue']['status'])
                last_committer = json_branch['committer_email']

                branch_object = Branch(json_branch['name'],
                                       repo,
                                       jira_issue=jira_issue,
                                       last_committer=last_committer
                                       )
                branches.append(branch_object)
        return branches

    def store_branches(self, branches):
        cache_path = self.config.get_cache_path()
        base_dict = dict()
        base_dict[BRANCHES] = branches

        with open(cache_path, 'w') as branches_file:
            json.dump(base_dict, branches_file, default=lambda x: x.__dict__)

    def get_json_issue(self, key):
        if key is None:  # because of CFY-GIVEAWAY
            return key
        json_issue = requests.get(Issue.JIRA_API_URL +
                                  key +
                                  '?fields=status')
        return json_issue.text

    def parse_json_issue(self, json_issue):
        if json_issue is None:  # because of CFY-GIVEAWAY
            return json_issue
        detailed_issue = json.loads(json_issue)
        issue = Issue(detailed_issue['key'],
                      detailed_issue['fields']['status']['name'])
        return issue

    def get_issue(self, key):
        json_issue = self.get_json_issue(key)
        issue = self.parse_json_issue(json_issue)
        return issue

    def add_commiter_and_date(self, branch):
        url = os.path.join(GITHUB_API_URL,
                           REPOS,
                           self.config.org_name,
                           branch.containing_repo.name,
                           BRANCHES,
                           branch.name
                           )
        s = requests.get(url, auth=(os.environ[GITHUB_USER],
                                    os.environ[GITHUB_PASS])).text
        json_details = json.loads(s)
        branch.committer_email = \
            json_details['commit']['commit']['author']['email']
        # Remember to add dates, preferably in a date-Object format
        # Ask Nir how to convert GitHub's time/date representation
        # to a python object.

    def add_committers_and_dates(self, query_branches):

        self.performance.detailed_branches_start = time.time()

        number_of_threads = \
            self.determine_number_of_threads(len(query_branches))
        pool = ThreadPool(number_of_threads)
        pool.map(self.add_commiter_and_date, query_branches)

        self.performance.detailed_branches_end = time.time()

    def update_branch_with_issue(self, branch):
        key = Issue.extract_issue_key(branch)
        issue = self.get_issue(key)
        branch.jira_issue = issue

    def update_branches_with_issues(self, branches):

        self.performance.issues_start = time.time()

        number_of_threads = self.determine_number_of_threads(len(branches))
        pool = ThreadPool(number_of_threads)
        pool.map(self.update_branch_with_issue, branches)

        self.performance.issues_end = time.time()


class BranchQuerySurplus(BranchQuery):

    DESCRIPTION = 'list all the surplus branches'
    FILENAME = 'surplus_branches.json'

    def __init__(self, query_config):
        super(BranchQuerySurplus, self).__init__(query_config)
        self.config.filename = BranchQuerySurplus.FILENAME

    def filter_branches(self, branches):
        return filter(BranchQuerySurplus.name_filter, branches)

    @staticmethod
    def name_filter(branch):

        branch_name = branch.name

        re_master_branch = re.compile('^master$')
        master_branch_cond = re_master_branch.search(branch_name)

        re_build_branch = re.compile('-build$')
        build_branch_cond = re_build_branch.search(branch_name)

        re_cfy_branch = re.compile('(CFY)-*(\d)+')
        cfy_branch_cond = re_cfy_branch.search(branch_name)

        return (not master_branch_cond and
                not build_branch_cond and
                not cfy_branch_cond)


class BranchQueryCfy(BranchQuery):

    DESCRIPTION = 'list all branches that include \'CFY\' in their name ' \
                  'and their corresponding JIRA issue status is either ' \
                  '\'Closed\' or \'Resolved\''
    FILENAME = 'cfy_branches.json'

    def __init__(self, query_config):
        super(BranchQueryCfy, self).__init__(query_config)
        self.config.filename = BranchQueryCfy.FILENAME

    @staticmethod
    def name_filter(branch):

        branch_name = branch.name

        re_cfy_branch = re.compile('CFY')
        cfy_branch_cond = re_cfy_branch.search(branch_name)

        return cfy_branch_cond

    def issue_filter(self, branch):
        if branch.jira_issue is None:  # because of CFY-GIVEAWAY
            return True

        issue_status = branch.jira_issue.status

        return issue_status == Issue.STATUS_CLOSED or \
            issue_status == Issue.STATUS_RESOLVED

    def filter_branches(self, branches):
        branches_that_contain_cfy = filter(self.name_filter, branches)
        self.update_branches_with_issues(branches_that_contain_cfy)
        return filter(self.issue_filter, branches_that_contain_cfy)
