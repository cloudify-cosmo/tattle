import os
import re
import tempfile

PROJECT_NAME = 'Tattle'


class Filter(object):

    NAME_FILTER = 'name'
    ISSUE_FILTER = 'issue'

    FILTERS = {NAME_FILTER: NameFilter, ISSUE_FILTER: IssueFilter}

    @classmethod
    def from_yaml(cls, yaml_filter):
        filter_class = cls.FILTERS[yaml_filter.type]
        return filter_class(yaml_filter)


class NameFilter(Filter):

    REGEXES = 'regular_expressions'

    def __init__(self, regexes):

        self.regexes = regexes

    @classmethod
    def from_yaml(cls, yaml_nf):

        regexes = yaml_nf.get(cls.REGEXES, list())

        return cls(regexes)

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
                 jira_team_name,
                 jira_statuses,
                 transform):
        self.jira_team_name = jira_team_name
        self.jira_statuses = jira_statuses
        self.transform = transform

    @classmethod
    def from_yaml(cls, yaml_if):
        jira_team_name = yaml_if.get(cls.JIRA_TEAM_NAME)
        jira_statuses = yaml_if.get(cls.JIRA_STATUSES)
        # we should add a default value, and it will be a list of the the jira issue statuses.
        # (see the comment under the 'ISSUE' class).
        # in addition, maybe we should enforce the provided jira_statuses list
        # to include only values from the jira issue status list.
        # an implementation option for that is using a descriptor,
        # like PerformanceTime in the old engine.py
        transform = yaml_if.get(cls.TRANSFORM, None)

        return cls(jira_team_name, jira_statuses, transform)


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

    def num_of_threads(self, items):
        if self.max_threads == self.NO_THREAD_LIMIT:
            return len(items)
        return min(self.max_threads, len(items))


class Issue(object):

    # the class Issue will include a static list of all the jira status.
    # this is because we need the whole list to be a default value in
    # the from_yaml, so when we will filter according to the statuses,
    # if no status list was supplied, then no issue will be filter by it's status

    STATUSES = []  # TODO ask ran or idan for our list of jira statuses.
    # TODO (cont.) remember that you can create custom statuses.

class Query(object):

    BRANCH = 'branch'

    QUERIES = {BRANCH: BranchFilter}

    def __init__(self, config, filters):

        self.config = config
        self.filters = filters

    @classmethod
    def from_config(cls, config):

        query_class = cls.QUERIES[config.data_type]()
        return query_class(config)


class BranchFilter(Filter):

    pass


























