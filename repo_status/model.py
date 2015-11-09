import abc
import itertools
import json
import logging
import os
import posixpath
import re
import requests
import sys
import time


from multiprocessing.dummy import Pool as ThreadPool

USE_CACHE_MODE = 'use-cache'
UP_TO_DATE_MODE = 'up-to-date'

BRANCHES = 'branches'
REPO = 'repo'
REPOS = 'repos'
ORGS = 'orgs'
TAGS = 'tags'
JIRA_ISSUE = 'jira_issue'

GITHUB_API_URL = 'https://api.github.com/'
CLOUDIFY_COSMO = 'cloudify-cosmo'
PUBLIC_REPOS = 'public_repos'
TOTAL_PRIVATE_REPOS = 'total_private_repos'
REPOS_PER_PAGE = 100
USERNAME = 'AviaE'
PASSWORD = 'A1b2Y8z9'
os.environ['GITHUB_USER'] = 'AviaE'  # remove this later
os.environ['GITHUB_PASS'] = 'A1b2Y8z9'  # remove this later
GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'

logger = logging.getLogger('model')
logger.setLevel(logging.DEBUG)
ish = logging.StreamHandler(sys.stdout)
ish.setLevel(logging.INFO)
info_formatter = logging.Formatter('%(asctime)s - %(message)s...', '%Y-%m-%d %H:%M:%S')
ish.setFormatter(info_formatter)
logger.addHandler(ish)

# create classes:
#   NameFilter, which has a list of regex filters
#       (in the future, it can also contain attributes that tell us if we should
#       'or' or 'and' the elements of the list, and/or negate the final result)
#   IssueFilter, which has a list of JIRA issues statuses
#       (what is said about the regex filter list of NameFilter can be said
#       about the above list)
#       a 'base for transform' which is a part of the branch's name which is to
#       transformed (created with a regex search, exactly like in the current
#       extract_issue_key()
#       and a NameTransform object which has a from and a to attributes, both are strings.
#       this object helps transform the transform_base to an issue key.
#       maybe even the two latter are a part of a BranchToIssueTransform
#       (or maybe it is just a 'Transform', and it has a base, from and to attributes.
#
# and change QueryConfig accordingly


class NameFilter(object):

    REGEXES = 'regular_expressions'

    def __init__(self, regex_list):

        self.regex_list = regex_list

    @classmethod
    def from_yaml(cls, yaml_nf):

        if yaml_nf is None:
            return None

        templates = yaml_nf.get(cls.REGEXES, list())
        regex_list = [re.compile(t) for t in templates]

        return cls(regex_list)






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


class Branch(GitHubObject):

    def __init__(self,
                 name,
                 repo,
                 jira_issue=None,
                 committer_email=''
                 ):
        super(Branch, self).__init__(name)
        self.repo = repo
        self.jira_issue = jira_issue
        self.committer_email = committer_email

    @classmethod
    def from_json(cls, json_branch):

        repo = None if json_branch[REPO] is None \
            else Repo(json_branch[REPO]['name'])

        jira_issue = None if json_branch[JIRA_ISSUE] is None \
            else Issue(json_branch[JIRA_ISSUE]['key'],
                       json_branch[JIRA_ISSUE]['status'])
        last_committer = json_branch['committer_email']

        return cls(json_branch['name'],
                   repo,
                   jira_issue=jira_issue,
                   committer_email=last_committer
                   )

    def __str__(self):
        issue = '' if self.jira_issue is None else str(self.jira_issue)

        return 'Branch name: {0}\n{1}Last committer: {2}\n'. \
            format(self.name, issue, self.committer_email.encode('utf-8'))


class Tag(GitHubObject):

    def __init__(self, name, repo):
        super(Tag, self).__init__(name)
        self.repo = repo

    @classmethod
    def from_json(cls, json_tag):
        return cls(json_tag['name'], Repo(json_tag['repo']))

    def __str__(self):
        return 'Tag: {0}'.format(self.name)

    def __repr__(self):
        return 'Tag(name={0})'.format(self.name)


class Issue(object):

    JIRA_API_URL = 'https://cloudifysource.atlassian.net/rest/api/2/issue/'
    JIRA_STR_TEMPLATE = u'JIRA status: {0}\n'
    STATUS_CLOSED = u'Closed'
    STATUS_RESOLVED = u'Resolved'

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
        return self.JIRA_STR_TEMPLATE.format(self.status)

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
                 mode,
                 filename,
                 max_threads=NO_THREAD_LIMIT,
                 org_name=CLOUDIFY_COSMO,
                 name_filter=None):

        self.resources_path = resources_path
        self.mode = mode
        self.filename = filename
        self.max_threads = max_threads
        self.org_name = org_name
        self.cache_path = os.path.join(resources_path, filename)
        self.name_filter = name_filter


class PerformanceTime(object):
    """
    for xQueryPerformance time attributes
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.name]

    def __set__(self, instance, value):

        if not isinstance(value, type(time.time())):
            raise TypeError('Expected an float')  # or time.time()-ish object?

        if value < 0:
            raise ValueError('Expected a non-negative value')

        instance.__dict__[self.name] = value


class TimeDelta(object):

    start = PerformanceTime('start')
    end = PerformanceTime('end')

    def __init__(self):

        self.start = 0.0
        self.end = 0.0
        self.value = 0.0

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, type, value, traceback):
        self.end = time.time()
        self.value = (self.end - self.start) * 1000


class QueryPerformance(object):

    ACTION_PERFORMANCE_TEMPLATE = '\naction:\n{0}\n'
    TOTAL_PERFORMANCE_TEMPLATE = 'total time: {0}ms'
    REPOS_PERFORMANCE_TEMPLATE = 'getting the repos: {0}ms'

    def __init__(self):
        self.total = TimeDelta()
        self.repos = TimeDelta()


class BranchQueryPerformance(QueryPerformance):

    BASIC_BRANCHES_PERFORMANCE_TEMPLATE = 'getting basic branch info: {0}ms'
    DETAILED_BRANCHES_PERFORMANCE_TEMPLATE = \
        'getting detailed branch info: {0}ms'

    basic_branches_start = PerformanceTime('basic_branches_start')
    basic_branches_end = PerformanceTime('basic_branches_end')
    detailed_branches_start = PerformanceTime('detailed_branches_start')
    detailed_branches_end = PerformanceTime('detailed_branches_end')

    def __init__(self):
        super(BranchQueryPerformance, self).__init__()
        self.basic_branches = TimeDelta()
        self.detailed_branches = TimeDelta()


class BranchQueryStalePerformance(BranchQueryPerformance):

    ISSUES_PERFORMANCE_TEMPLATE = 'getting the issues: {0}ms'

    issues_start = PerformanceTime('issues_start')
    issues_end = PerformanceTime('issues_end')

    def __init__(self):
        super(BranchQueryStalePerformance, self).__init__()
        self.issues = TimeDelta()


class TagQueryPerformance(QueryPerformance):

    TAGS_PERFORMANCE_TEMPLATE = 'getting the tags: {0}ms'

    tags_start = PerformanceTime('tags_start')
    tags_end = PerformanceTime('tags_end')

    def __init__(self):
        super(TagQueryPerformance, self).__init__()
        self.tags = TimeDelta()


class Query(object):

    __metaclass__ = abc.ABCMeta

    DESCRIPTION = None

    @abc.abstractmethod
    def filter_items(self, branches):
        logger.info('filtering the requested data by the query criteria')
        pass

    @abc.abstractmethod
    def query(self):
        pass

    def __init__(self, query_config=None):
        self.config = query_config
        self.data_type = None
        self.performance = QueryPerformance()
        self.result = None

    def determine_number_of_threads(self, number_of_calls):
        max_number_of_threads = self.config.max_threads
        if max_number_of_threads == QueryConfig.NO_THREAD_LIMIT:
            return number_of_calls
        else:
            return min(number_of_calls, max_number_of_threads)

    def process(self):
        logger.info('processing query')
        if self.config.mode == UP_TO_DATE_MODE:

            self.result = self.query()
            self.store()

        elif self.config.mode == USE_CACHE_MODE:

            self.result = self.load_from_cache()

    def store(self):
        with open(self.config.cache_path, 'w') as cache_file:
            json.dump(self.result, cache_file, default=lambda x: x.__dict__)

    def load_from_cache(self):
        items = []
        with open(self.config.cache_path, 'r') as cache_file:
            json_items = json.load(cache_file)
            for json_item in json_items:

                item = self.data_type.from_json(json_item)
                items.append(item)
        return items

    def output(self):
        cur_repo_name = None

        for item in self.result:
            running_repo_name = item.repo.name
            if cur_repo_name != running_repo_name:
                if cur_repo_name is not None:
                    print ''
                cur_repo_name = running_repo_name
                print '*' * (len(str(item.repo)))
                print str(item.repo)
                print '*' * (len(str(item.repo)))

            print item

    def print_performance(self):

        print self.performance.ACTION_PERFORMANCE_TEMPLATE \
            .format(self.DESCRIPTION)
        print self.performance.TOTAL_PERFORMANCE_TEMPLATE \
            .format(self.performance.total.value)
        print ('-' * len(self.performance.TOTAL_PERFORMANCE_TEMPLATE
                         .format(self.performance.total.value)))
        print self.performance.REPOS_PERFORMANCE_TEMPLATE \
            .format(self.performance.repos.value)

    def get_num_of_repos(self):

        url = posixpath.join(GITHUB_API_URL,
                             ORGS,
                             self.config.org_name
                             )
        r = requests.get(url,
                         auth=(os.environ[GITHUB_USER],
                               os.environ[GITHUB_PASS]))
        json_repos = json.loads(r.text)

        return json_repos[PUBLIC_REPOS] + json_repos[TOTAL_PRIVATE_REPOS]

    def get_json_repos(self, page_number):

        pagination_parameters = '?page={0}&per_page={1}' \
            .format(page_number, REPOS_PER_PAGE)

        url = posixpath.join(GITHUB_API_URL,
                             ORGS,
                             self.config.org_name,
                             REPOS + pagination_parameters,
                             )
        response = requests.get(url, auth=(os.environ[GITHUB_USER],
                                           os.environ[GITHUB_PASS]))
        return json.loads(response.text)

    def parse_json_repo(self, json_repo):
        return Repo(json_repo['name'])

    def get_repos(self):
        logger.info('retrieving github repositories for the {0} organization'
                    .format(self.config.org_name))
        self.performance.repos_start = time.time()

        num_of_repos = self.get_num_of_repos()
        num_of_threads = \
            self.determine_number_of_threads(num_of_repos / 100 + 1)

        pool = ThreadPool(num_of_threads)
        json_repos = pool.map(self.get_json_repos, range(1, num_of_threads+1))
        repos = []
        for list_of_json_repos in json_repos:
            for json_repo in list_of_json_repos:
                repos.append(self.parse_json_repo(json_repo))

        self.performance.repos_end = time.time()
        return repos


class BranchQuery(Query):

    DESCRIPTION = None

    def filter_items(self, branches):
        super(BranchQuery, self).filter_items(branches)

    def __init__(self, query_config=None):
        super(BranchQuery, self).__init__(query_config)
        self.data_type = Branch
        self.performance = BranchQueryPerformance()

    def query(self):

        with self.performance.repos:
            repos = self.get_repos()
        with self.performance.basic_branches:
            branches = self.get_org_branches(repos)
        query_branches = self.filter_items(branches)
        with self.performance.detailed_branches:
            self.add_committers_and_dates(query_branches)
        return query_branches

    def print_performance(self):
        super(BranchQuery, self).print_performance()
        print self.performance.BASIC_BRANCHES_PERFORMANCE_TEMPLATE \
            .format(self.performance.basic_branches.value)
        print self.performance.DETAILED_BRANCHES_PERFORMANCE_TEMPLATE \
            .format(self.performance.detailed_branches.value)

    def get_json_branches(self, repo_name):

        url = posixpath.join(GITHUB_API_URL,
                             REPOS,
                             self.config.org_name,
                             repo_name,
                             BRANCHES
                             )
        r = requests.get(url, auth=(os.environ[GITHUB_USER],
                                    os.environ[GITHUB_PASS]))
        return json.loads(r.text)

    def parse_json_branches(self, json_branches, repo):

        branches = [Branch(jb['name'], repo) for jb in json_branches]
        return branches

    def get_branches(self, repo):

        json_branches = self.get_json_branches(repo.name)
        branch_list = self.parse_json_branches(json_branches, repo)

        return sorted(branch_list)

    def get_org_branches(self, repos):
        logger.info('retrieving basic github branch info for the {0} organization'
                    .format(self.config.org_name))
        num_of_threads = self.determine_number_of_threads(len(repos))
        pool = ThreadPool(num_of_threads)
        branches_lists = pool.map(self.get_branches, repos)
        return list(itertools.chain.from_iterable(branches_lists))

    def add_committer_and_date(self, branch):
        url = posixpath.join(GITHUB_API_URL,
                             REPOS,
                             self.config.org_name,
                             branch.repo.name,
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
        logger.info('retrieving detailed github branch info for the {0} '
                    'organization (queried branches only)'
                    .format(self.config.org_name))
        number_of_threads = \
            self.determine_number_of_threads(len(query_branches))
        pool = ThreadPool(number_of_threads)
        pool.map(self.add_committer_and_date, query_branches)


class BranchQuerySurplus(BranchQuery):

    DESCRIPTION = 'list all the surplus branches'
    FILENAME = 'surplus_branches.json'

    def __init__(self, query_config=None):
        super(BranchQuerySurplus, self).__init__(query_config)

    def filter_items(self, branches):
        super(BranchQuerySurplus, self).filter_items(branches)
        return filter(BranchQuerySurplus.name_filter, branches)

    @staticmethod
    def name_filter(branch):

        master_branch_re = re.compile('^master$')
        master_branch_cond = master_branch_re.search(branch.name)

        build_branch_re = re.compile('-build$')
        build_branch_cond = build_branch_re.search(branch.name)

        cfy_branch_re = re.compile('(CFY)-*(\d)+')
        cfy_branch_cond = cfy_branch_re.search(branch.name)

        return (not master_branch_cond and
                not build_branch_cond and
                not cfy_branch_cond)


class BranchQueryStale(BranchQuery):

    DESCRIPTION = 'list all the \'stale\' branches - \n' \
                  '(branches that include \'CFY\' in their name ' \
                  'and their corresponding JIRA issue status is either ' \
                  '\'Closed\' or \'Resolved\')'
    FILENAME = 'stale_branches.json'

    def __init__(self, query_config=None):
        super(BranchQueryStale, self).__init__(query_config)
        self.performance = BranchQueryStalePerformance()

    def print_performance(self):
        super(BranchQueryStale, self).print_performance()
        print self.performance.ISSUES_PERFORMANCE_TEMPLATE \
            .format(self.performance.issues.value)

    @staticmethod
    def name_filter(branch):

        branch_name = branch.name

        cfy_branch_re = re.compile('CFY')
        cfy_branch_cond = cfy_branch_re.search(branch_name)

        return cfy_branch_cond

    def issue_filter(self, branch):
        if branch.jira_issue is None:  # because of CFY-GIVEAWAY
            return True

        issue_status = branch.jira_issue.status

        return issue_status == Issue.STATUS_CLOSED or \
            issue_status == Issue.STATUS_RESOLVED

    def filter_items(self, branches):
        super(BranchQueryStale, self).filter_items(branches)
        branches_that_contain_cfy = filter(self.name_filter, branches)
        with self.performance.issues:
            self.update_branches_with_issues(branches_that_contain_cfy)
        return filter(self.issue_filter, branches_that_contain_cfy)

    def get_json_issue(self, key):
        if key is None:  # because of CFY-GIVEAWAY
            return key
        json_issue = requests.get(Issue.JIRA_API_URL +
                                  key +
                                  '?fields=status')
        return json.loads(json_issue.text)

    def parse_json_issue(self, json_issue):
        if json_issue is None:  # because of CFY-GIVEAWAY
            return json_issue

        issue = Issue(json_issue['key'],
                      json_issue['fields']['status']['name'])
        return issue

    def get_issue(self, key):
        json_issue = self.get_json_issue(key)
        issue = self.parse_json_issue(json_issue)
        return issue

    def update_branch_with_issue(self, branch):
        key = Issue.extract_issue_key(branch)
        issue = self.get_issue(key)
        branch.jira_issue = issue

    def update_branches_with_issues(self, branches):
        logger.info('retrieving JIRA issues'
                    .format(self.config.org_name))
        number_of_threads = self.determine_number_of_threads(len(branches))
        pool = ThreadPool(number_of_threads)
        pool.map(self.update_branch_with_issue, branches)


class TagQuery(Query):

    DESCRIPTION = 'list all tags whose name doesn\'t satisfy convention'
    FILENAME = 'tags.json'

    def __init__(self, query_config=None):
        super(TagQuery, self).__init__(query_config)
        self.data_type = Tag
        self.performance = TagQueryPerformance()

    def filter_items(self, tags):
        return filter(TagQuery.name_filter, tags)

    @staticmethod
    def name_filter(tag):

        release_tag_re = re.compile('^\d(.\d)*$')  # maybe make all the regex strings raw.
        release_tag_cond = release_tag_re.search(tag.name)

        milestone_tag_re = re.compile('^\d(.\d)*m\d$')
        milestone_tag_cond = milestone_tag_re.search(tag.name)

        rc_tag_re = re.compile('^\d(.\d)*rc\d$')
        rc_tag_cond = rc_tag_re.search(tag.name)

        return (not release_tag_cond and
                not milestone_tag_cond and
                not rc_tag_cond)

    def query(self):

        with self.performance.repos:
            repos = self.get_repos()
        with self.performance.tags:
            tags = self.get_org_tags(repos)
        query_tags = self.filter_items(tags)
        return query_tags

    def print_performance(self):
        super(TagQuery, self).print_performance()
        print self.performance.TAGS_PERFORMANCE_TEMPLATE \
            .format(self.performance.tags.value)

    def get_org_tags(self, repos):
        logger.info('retrieving github tags for the {0} organization'
                    .format(self.config.org_name))
        num_of_threads = self.determine_number_of_threads(len(repos))
        pool = ThreadPool(num_of_threads)
        tags_lists = pool.map(self.get_tags, repos)

        return list(itertools.chain.from_iterable(tags_lists))

    def get_tags(self, repo):

        json_tags = self.get_json_tags(repo.name)
        tag_list = self.parse_json_tags(json_tags, repo)

        return sorted(tag_list)

    def get_json_tags(self, repo_name):

        url = posixpath.join(GITHUB_API_URL,
                             REPOS,
                             self.config.org_name,
                             repo_name,
                             TAGS
                             )
        r = requests.get(url, auth=(os.environ[GITHUB_USER],
                                    os.environ[GITHUB_PASS]))
        return json.loads(r.text)

    def parse_json_tags(self, json_tags, repo):

        tags = [Tag(jt['name'], repo) for jt in json_tags]
        return tags
