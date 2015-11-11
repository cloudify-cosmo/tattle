import argparse
import os
import tempfile
import yaml
import sys

from repo_status.model import QueryConfig
from repo_status.model import NameFilter
from repo_status.model import JiraIssueFilter

GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
CONFIG_PATH_COMMAND_NAME = '--config-path'
CONFIG_PATH_HELP_TEXT = 'a path to a YAML configuration file'

GITHUB_ENV_VARS_DONT_EXIST = 'GitHub authentication environment variables' \
                             ' do not exist.\nPlease define them: ' \
                             '[GITHUB_USER], [GITHUB_PASS], and try again.'

ARGUMENT_PARSER_DESCRIPTION = 'Perform simple queries on your GitHub branches'

MAX_THREADS = 'max_threads'
GITHUB_ORG_NAME = 'github_org_name'

OUTPUT_PATH = 'output path'
DEFAULT_OUTPUT_PATH = os.path.join(tempfile.gettempdir(),
                                   'cloudify-repo-status/report.json')
NAME_FILTER = 'name_filter'
ISSUE_FILTER = 'issue_filter'


def enforce_github_env_variables():

    try:
        user = os.environ[GITHUB_USER]  # not assigning these causes a warning
        password = os.environ[GITHUB_PASS]
    except KeyError:
        sys.exit(GITHUB_ENV_VARS_DONT_EXIST)


def parse_arguments():

    parser = argparse.ArgumentParser(description=ARGUMENT_PARSER_DESCRIPTION)
    parser.add_argument('-c', CONFIG_PATH_COMMAND_NAME,
                        type=str,
                        help=CONFIG_PATH_HELP_TEXT)

    return parser.parse_args()


def create_query_config(args):
    try:
        with open(args.config_path) as config_file:
            yaml_config = yaml.load(config_file)

            max_threads = yaml_config.get(MAX_THREADS,
                                          QueryConfig.NO_THREAD_LIMIT)
            github_org_name = yaml_config.get(GITHUB_ORG_NAME)

            filters = list()
            filters.append(NameFilter.from_yaml(
                yaml_config.get(NAME_FILTER, None)))
            filters.append(JiraIssueFilter.from_yaml(
                yaml_config.get(ISSUE_FILTER, None)))

            output_path = yaml_config.get(OUTPUT_PATH,
                                          DEFAULT_OUTPUT_PATH)

            return QueryConfig(max_threads,
                               github_org_name,
                               filters,
                               output_path,
                               )
    except IOError as error:
        sys.exit(error)


def main():

    # enforce_github_env_variables()
    args = parse_arguments()
    try:
        with open(args.config_path) as config_file:
            yaml_config = yaml.load(config_file)
    except IOError as error:
        sys.exit(error)

    qc = QueryConfig.from_yaml(yaml_config)


    # first create the QC. with a QC.from_yaml.
    # this means that all the constants will move to QC.
    # then create a xQuery with a factory
    # according to the data_type field of query_config.
    # maybe give the factory the whole QC object,
    # and inside the factory we will extract the data_type.

if __name__ == '__main__':
    main()
