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
NO_THREAD_LIMIT = -1
os.environ['GITHUB_USER'] = 'AviaE' # remove this later
os.environ['GITHUB_PASS'] = 'A1b2Y8z9' # remove this later
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

    @staticmethod
    def get_json_repos(org_name=CLOUDIFY_COSMO):

        full_address = os.path.join(GITHUB_API_URL,
                                    'orgs',
                                    org_name,
                                    'repos')
        r = requests.get(full_address,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS])
                         )

        return r.text

    @staticmethod
    def parse_json_repos(json_repos):

        detailed_list_of_repos = json.loads(json_repos)
        list_of_repo_objects = [Repo(dr['name'])
                                for dr in detailed_list_of_repos]

        return list_of_repo_objects

    @staticmethod
    def get_repos(org_name=CLOUDIFY_COSMO):
        json_repos = Repo.get_json_repos(org_name)
        repo_list = Repo.parse_json_repos(json_repos)
        return sorted(repo_list)


class Branch:

    # Idan wants to add information about creator name and create time.
    # But it seems we can only add this information regarding the last commit.

    def __init__(self, name, containing_repo=Repo()):
        self.name = name
        self.containing_repo = containing_repo

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def __lt__(self, other):
        return self.name <= other.name

    @staticmethod
    def get_json_branches(repo_name, org_name=CLOUDIFY_COSMO):

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

    @staticmethod
    def parse_json_branches(json_branches, repo_object=Repo()):
        detailed_list_of_branches = json.loads(json_branches)
        list_of_branch_objects = [Branch(db['name'], repo_object)
                                  for db in detailed_list_of_branches]

        return list_of_branch_objects

    @staticmethod
    def get_branches(repo_object=Repo(), org_name=CLOUDIFY_COSMO):

        json_branches = Branch.get_json_branches(repo_object.name, org_name)
        branch_list = Branch.parse_json_branches(json_branches, repo_object)

        return sorted(branch_list)

    @staticmethod
    def get_org_branches(org_name=CLOUDIFY_COSMO):

        repos = Repo.get_repos(org_name)
        pool = ThreadPool(len(repos))

        branches_lists = pool.map(Branch.get_branches, repos)
        return list(itertools.chain.from_iterable(branches_lists))

    @staticmethod
    def load_branches(json_filename):

        branches = []
        with open(json_filename, 'r') as branches_file:
            str_branches_dict = json.load(branches_file)
            for str_branch in str_branches_dict['branches']:
                branch_object = Branch(str_branch['name'],
                                       Repo(str_branch['containing_repo']
                                                      ['name']))
                branches.append(branch_object)
        return branches

    @staticmethod
    def store_branches(branches, json_filepath):
        base_dict = dict()
        base_dict['branches'] = branches
        containing_dir = os.path.dirname(os.path.realpath(json_filepath))
        if not os.path.isdir(containing_dir):
            os.makedirs(containing_dir)

        with open(json_filepath, 'w') as branches_file:
            json.dump(base_dict, branches_file, default=lambda x: x.__dict__)

    @staticmethod
    def update_branch_cache(cache_filename):
        branches = Branch.get_org_branches()
        Branch.store_branches(branches, cache_filename)


class Issue:

    _JIRA_API_URL = 'https://cloudifysource.atlassian.net/rest/api/2/issue/'

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
    def load_issues(filename):
        issues = []
        with open(filename, 'r') as issues_file:
            str_issues_dict = json.load(issues_file)
            for str_issue in str_issues_dict['issues']:
                issue = Issue(str_issue['key'],
                              str_issue['status'])
                issues.append(issue)
        return issues

    @staticmethod
    def get_json_issue(key):
        json_issue = requests.get(Issue._JIRA_API_URL +
                                  key +
                                  '?fields=status')
        return json_issue.text

    @staticmethod
    def parse_json_issue(json_issue):
        detailed_issue = json.loads(json_issue)
        issue = Issue(detailed_issue['key'],
                      detailed_issue['fields']['status']['name'])
        return issue

    @staticmethod
    def get_issue(key):
        json_issue = Issue.get_json_issue(key)
        issue = Issue.parse_json_issue(json_issue)
        return issue

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

    @staticmethod
    def store_issues(issues, json_filepath):
        base_dict = dict()
        base_dict['issues'] = issues

        containing_dir = os.path.dirname(os.path.realpath(json_filepath))
        if not os.path.isdir(containing_dir):
            os.makedirs(containing_dir)

        with open(json_filepath, 'w') as issue_file:
            json.dump(base_dict, issue_file, default=lambda x: x.__dict__)

    @staticmethod
    def update_issue_cache(branches_filename, issues_filename):
        branches = Branch.load_branches(branches_filename)

        issue_keys = filter(None,
                            [Issue.extract_issue_key(b) for b in branches]
                            )
        pool = ThreadPool(len(issue_keys))
        issues = pool.map(Issue.get_issue, issue_keys)
        Issue.store_issues(issues, issues_filename)


class QueryConfig(object):

    def __init__(self,
                 resources_path=RESOURCES_FOLDER_PATH,
                 max_threads=NO_THREAD_LIMIT):
        self.branches_file_path = resources_path + BRANCHES_FILENAME
        self.issues_file_path = resources_path + ISSUES_FILENAME
        self.max_threads = max_threads


class BranchQuery(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, query_config):
        self.query_config = query_config

    @abc.abstractmethod
    def update_cache(self):
        pass

    @abc.abstractmethod
    def branch_filter(self, branch):
        pass

    @abc.abstractmethod
    def output(self, branches):
        pass


class BranchQuerySurplus(BranchQuery):

    DESCRIPTION = 'list all the surplus branches'

    def __init__(self, query_config):
        super(BranchQuerySurplus, self).__init__(query_config)

    def update_cache(self):

        Branch.update_branch_cache(self.query_config.branches_file_path)

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

    def output(self, branches):

        cur_repo_name = None

        for surplus_branch in branches:
            running_repo_name = surplus_branch.containing_repo.name
            if cur_repo_name != running_repo_name:
                if cur_repo_name is not None:
                    print ''
                cur_repo_name = running_repo_name
                prefix = 'Repository: '
                print '*' * (len(cur_repo_name) + len(prefix))
                print prefix + cur_repo_name
                print '*' * (len(cur_repo_name) + len(prefix))

            print 'Branch: ' + surplus_branch.name


class BranchQueryCfy(BranchQuery):

    DESCRIPTION = 'list all branch that include \'CFY\' in their name ' \
                  'and their corresponding JIRA issue status is either' \
                  '\'Closed\' or \'Resolved\''

    def __init__(self, query_config):
        super(BranchQueryCfy, self).__init__(query_config)

    def update_cache(self):
        Branch.update_branch_cache(self.query_config.branches_file_path)
        Issue.update_issue_cache(self.query_config.branches_file_path,
                                 self.query_config.issues_file_path)

    def branch_filter(self, branch, issue_file=None):

        issues = set(Issue.load_issues(self.query_config.issues_file_path))
        issue_key = Issue.extract_issue_key(branch)

        return Issue(issue_key, 'Closed') in issues or \
            Issue(issue_key, 'Resolved') in issues

    def output(self, branches):

        cur_repo_name = None

        for surplus_branch in branches:
            running_repo_name = surplus_branch.containing_repo.name
            if cur_repo_name != running_repo_name:
                if cur_repo_name is not None:
                    print ''
                cur_repo_name = running_repo_name
                prefix = 'Repository: '
                print '*' * (len(cur_repo_name) + len(prefix))
                print prefix + cur_repo_name
                print '*' * (len(cur_repo_name) + len(prefix))

            print 'Branch: ' + surplus_branch.name
