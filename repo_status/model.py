import abc
import itertools
import json
import os
import re
import requests

from multiprocessing.dummy import Pool as ThreadPool

GITHUB_API_URL = 'https://api.github.com/'
CLOUDIFY_COSMO = 'cloudify-cosmo'
USERNAME = 'AviaE'
PASSWORD = 'A1b2Y8z9'
os.environ['GITHUB_USER'] = 'AviaE'  # remove this later
os.environ['GITHUB_PASS'] = 'A1b2Y8z9'  # remove this later
GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
BRANCHES_FILENAME = 'branches.json'
ISSUES_FILENAME = 'issues.json'
RESOURCES_FOLDER_PATH = \
    os.path.join(os.environ['HOME'],
                 '.cloudify-repo-status/resources/')


class Repo:

    def __init__(self, name='sample name'):
        self.name = name

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __lt__(self, other):
        return self.name <= other.name


class Branch:

    def __init__(self, name, containing_repo=Repo()):
        self.name = name
        self.containing_repo = containing_repo

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __lt__(self, other):
        return self.name <= other.name


class Issue:

    JIRA_API_URL = 'https://cloudifysource.atlassian.net/rest/api/2/issue/'

    def __init__(self, key, status):
        self.key = key
        self.status = status

    def __hash__(self):
        return hash((self.key, self.status))

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

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
    BRANCHES_FILENAME = 'branches.json'
    ISSUES_FILENAME = 'issues.json'

    def __init__(self,
                 resources_path,
                 max_threads=NO_THREAD_LIMIT):
        self.resources_path = resources_path
        self.max_threads = max_threads
        self.branches_file_path = os.path.join(self.resources_path,
                                               BRANCHES_FILENAME)
        self.issues_file_path = os.path.join(self.resources_path,
                                             ISSUES_FILENAME)


class BranchQuery(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, query_config):
        self.query_config = query_config

    # does not include the caching of the branch details.
    # that is because we need the branch details only for cfy/surplus branches,
    # and we get them only after we filter them using the branch filter method.
    @abc.abstractmethod
    def update_cache(self):
        pass

    @abc.abstractmethod
    def branch_filter(self, branch):
        pass


    def output(self, branches):

        cur_repo_name = None

        for b in branches:
            running_repo_name = b.containing_repo.name
            if cur_repo_name != running_repo_name:
                if cur_repo_name is not None:
                    print ''
                cur_repo_name = running_repo_name
                prefix = 'Repository: '
                print '*' * (len(cur_repo_name) + len(prefix))
                print prefix + cur_repo_name
                print '*' * (len(cur_repo_name) + len(prefix))

            print 'Branch:   ' + b.name

    @staticmethod
    def determine_number_of_threads(number_of_calls, max_number_of_threads):

        if max_number_of_threads == QueryConfig.NO_THREAD_LIMIT:
            return number_of_calls
        else:
            return max_number_of_threads

    def get_json_repos(self, org_name=CLOUDIFY_COSMO):

        full_address = os.path.join(GITHUB_API_URL,
                                    'orgs',
                                    org_name,
                                    'repos')
        r = requests.get(full_address,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS])
                         )
        return r.text

    def parse_json_repos(self, json_repos):

        detailed_list_of_repos = json.loads(json_repos)
        list_of_repo_objects = [Repo(dr['name'])
                                for dr in detailed_list_of_repos]

        return list_of_repo_objects

    def get_repos(self, org_name=CLOUDIFY_COSMO):
        json_repos = self.get_json_repos(org_name)
        repo_list = self.parse_json_repos(json_repos)
        return sorted(repo_list)

    def get_json_branches(self, repo_name, org_name=CLOUDIFY_COSMO):

        full_address = os.path.join(GITHUB_API_URL,
                                    'repos',
                                    org_name,
                                    repo_name,
                                    'branches')
        r = requests.get(full_address,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS])
                         )
        return r.text

    def parse_json_branches(self, json_branches, repo_object=Repo()):
        detailed_list_of_branches = json.loads(json_branches)
        list_of_branch_objects = [Branch(db['name'], repo_object)
                                  for db in detailed_list_of_branches]

        return list_of_branch_objects

    def get_branches(self, repo_object=Repo(), org_name=CLOUDIFY_COSMO):

        json_branches = self.get_json_branches(repo_object.name, org_name)
        branch_list = self.parse_json_branches(json_branches, repo_object)

        return sorted(branch_list)

    def get_org_branches(self, org_name=CLOUDIFY_COSMO):

        repos = self.get_repos(org_name)
        num_of_threads = BranchQuery. \
            determine_number_of_threads(len(repos),
                                        self.query_config.max_threads)
        pool = ThreadPool(num_of_threads)

        branches_lists = pool.map(self.get_branches, repos)
        return list(itertools.chain.from_iterable(branches_lists))

    def load_branches(self):

        json_filename = self.query_config.branches_file_path
        branches = []
        with open(json_filename, 'r') as branches_file:
            str_branches_dict = json.load(branches_file)
            for str_branch in str_branches_dict['branches']:
                branch_object = Branch(str_branch['name'],
                                       Repo(str_branch['containing_repo']
                                                      ['name']))
                branches.append(branch_object)
        return branches

    def store_branches(self, branches, json_filepath):
        base_dict = dict()
        base_dict['branches'] = branches
        containing_dir = os.path.dirname(os.path.realpath(json_filepath))
        if not os.path.isdir(containing_dir):
            os.makedirs(containing_dir)

        with open(json_filepath, 'w') as branches_file:
            json.dump(base_dict, branches_file, default=lambda x: x.__dict__)

    def update_branch_cache(self, cache_filename):
        branches = self.get_org_branches()
        self.store_branches(branches, cache_filename)

    def load_issues(self, filename):
        issues = []
        with open(filename, 'r') as issues_file:
            str_issues_dict = json.load(issues_file)
            for str_issue in str_issues_dict['issues']:
                issue = Issue(str_issue['key'],
                              str_issue['status'])
                issues.append(issue)
        return issues

    def get_json_issue(self, key):
        json_issue = requests.get(Issue.JIRA_API_URL +
                                  key +
                                  '?fields=status')
        return json_issue.text

    def parse_json_issue(self, json_issue):
        detailed_issue = json.loads(json_issue)
        issue = Issue(detailed_issue['key'],
                      detailed_issue['fields']['status']['name'])
        return issue

    def get_issue(self, key):
        json_issue = self.get_json_issue(key)
        issue = self.parse_json_issue(json_issue)
        return issue

    def store_issues(self, issues, json_filepath):
        base_dict = dict()
        base_dict['issues'] = issues

        containing_dir = os.path.dirname(os.path.realpath(json_filepath))
        if not os.path.isdir(containing_dir):
            os.makedirs(containing_dir)

        with open(json_filepath, 'w') as issue_file:
            json.dump(base_dict, issue_file, default=lambda x: x.__dict__)

    def update_issue_cache(self, branches_filename, issues_filename):
        branches = self.load_branches()

        issue_keys = filter(None,
                            [Issue.extract_issue_key(b) for b in branches])

        num_of_threads = BranchQuery.\
            determine_number_of_threads(len(issue_keys),
                                        self.query_config.max_threads)

        pool = ThreadPool(num_of_threads)
        issues = pool.map(self.get_issue, issue_keys)
        self.store_issues(issues, issues_filename)


class BranchQuerySurplus(BranchQuery):

    DESCRIPTION = 'list all the surplus branches'

    def __init__(self, query_config):
        super(BranchQuerySurplus, self).__init__(query_config)

    def update_cache(self):

        self.update_branch_cache(self.query_config.branches_file_path)

    def branch_filter(self, branch):

        branch_name = branch.name

        re_master = re.compile('^master$')
        master_branch_cond = re_master.search(branch_name)

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

    def __init__(self, query_config):
        super(BranchQueryCfy, self).__init__(query_config)

    def update_cache(self):
        self.update_branch_cache(self.query_config.branches_file_path)
        self.update_issue_cache(self.query_config.branches_file_path,
                                self.query_config.issues_file_path)

    def branch_filter(self, branch, issue_file=None):

        issues = set(self.load_issues(self.query_config.issues_file_path))
        issue_key = Issue.extract_issue_key(branch)

        return Issue(issue_key, 'Closed') in issues or \
            Issue(issue_key, 'Resolved') in issues
