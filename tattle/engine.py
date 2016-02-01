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

import argparse
import os
import time
import yaml
import sys
import getpass

from tattle.model import QueryConfig
from tattle.model import Query
from tattle.model import Filter

GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
CONFIG_PATH_COMMAND_NAME = '--config-path'
CONFIG_PATH_HELP_TEXT = 'a path to a YAML configuration file'
ORG_NAME_COMMAND_NAME = '--org'
ORG_NAME_HELP_TEXT = 'GitHub organization to query'
BRANCH_NAME_COMMAND_NAME = '--branch-names'
BRANCH_NAME_HELP_TEXT = 'the branch names to query'
JIRA_TEAM_COMMAND_NAME = '--jira-team'
JIRA_TEAM_HELP_TEXT = 'the jira team to be searched'
JIRA_STATUSES_COMMAND_NAME = '--jira-statuses'
JIRA_STATUSES_HELP_TEXT = 'jira issue statuses that will be included in ' \
                          'the query, separated by space'
GITHUB_ENV_VARS_DONT_EXIST = 'GitHub authentication environment variables' \
                             ' do not exist.\nPlease define them: ' \
                             '[GITHUB_USER], [GITHUB_PASS], and try again.'
OUTPUT_PATH_COMMAND_NAME = '--output-path'
OUTPUT_PATH_HELP_TEXT = 'the path of tattle\'s output file, a report.json ' \
                        'file. If not specified, /tmp/Tattle/report.json ' \
                        'will be used.'
THREAD_LIMIT_COMMAND_NAME = '--thread-limit'
THREAD_LIMIT_HELP_TEXT = 'maximum number of threads used by tattle. Unless ' \
                         'specified, tattle will use all available ' \
                         'resources in order to perform as fast as it can.'

ARGUMENT_PARSER_DESCRIPTION = 'Perform simple queries on your GitHub branches'
USE_PASSWORD_PROMPT = 'Running tattle without a github username & password ' \
                      'will limit you to to 60 queries an hour. Would you ' \
                      'like to enter your GitHub username & password (y) [' \
                      'RECOMMENDED] or continue without entering GitHub ' \
                      'credentials (n)?'

PERFORMANCE_PRECISION = 3


def query_yes_no(question):
    """Ask a yes/no question via raw_input() and return their answer.

    :param question: a string that is presented to the user.

    :return: True for the user input 'y' and False for 'n'
    """
    valid = {'y': True, 'n': False}

    while True:
        sys.stdout.write(question + ' [Y/n]:')
        choice = raw_input().lower()
        if choice == '':
            # If the user just hits enter, then tattle assumes it's a 'y'.
            return True
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'y' (=yes) or 'n' (=no).\n")


def enforce_github_env_variables():
    """Checks and enforces Github credentials' environment variables.
    """
    try:
        github_user = os.environ[GITHUB_USER]
        github_pass = os.environ[GITHUB_PASS]
    except KeyError:
        if query_yes_no(USE_PASSWORD_PROMPT):
            github_user = raw_input('GitHub username:')
            github_pass = getpass.getpass(prompt='GitHub password:')
            os.environ[GITHUB_USER] = github_user
            os.environ[GITHUB_PASS] = github_pass


def parse_arguments():
    """Sets up CLI arguments.

    :return: CLI arguments
    """
    parser = argparse.ArgumentParser(description=ARGUMENT_PARSER_DESCRIPTION)
    parser.add_argument(CONFIG_PATH_COMMAND_NAME, '-c',
                        metavar='<PATH_TO_CONFIG>',
                        help=CONFIG_PATH_HELP_TEXT)
    parser.add_argument(ORG_NAME_COMMAND_NAME,
                        '-g',
                        metavar='<ORGANIZATION>',
                        help=ORG_NAME_HELP_TEXT)
    parser.add_argument(BRANCH_NAME_COMMAND_NAME,
                        '-b',
                        nargs='*',
                        metavar='<NAMES>',
                        help=BRANCH_NAME_HELP_TEXT)
    parser.add_argument(JIRA_TEAM_COMMAND_NAME,
                        '-j',
                        metavar='<JIRA-TEAM>',
                        help=JIRA_TEAM_HELP_TEXT)
    parser.add_argument(JIRA_STATUSES_COMMAND_NAME,
                        '-s',
                        nargs='*',
                        metavar='<JIRA-STATUS>',
                        help=JIRA_STATUSES_HELP_TEXT)
    parser.add_argument(OUTPUT_PATH_COMMAND_NAME,
                        '-o',
                        metavar='<OUTPUT-PATH>',
                        help=OUTPUT_PATH_HELP_TEXT)
    parser.add_argument(THREAD_LIMIT_COMMAND_NAME,
                        '-t',
                        metavar='<THREAD-LIMIT>',
                        type=int,
                        help=THREAD_LIMIT_HELP_TEXT)

    return parser.parse_args()


def get_filters_from_args(args):
    """Creates Filter objects from CLI arguments.

    :param args: CLI arguments.
    :return: List of created Filter objects.
    """
    filters_list = []

    if args.branch_names:
        filter_dict = {'type': 'name', 'regular_expressions':
            args.branch_names}
        filters_list.append(Filter.from_args(filter_dict))

    if args.jira_team:
        if hasattr(args, 'jira_statuses') and args.jira_statuses:
            jira_statuses = args.jira_statuses
        else:
            jira_statuses = []

        filter_dict = {'type': 'issue', 'jira_team_name': args.jira_team,
                         'jira_statuses': jira_statuses}
        filters_list.append(Filter.from_args(filter_dict))

    return filters_list


def print_performance(start, end):
    """ Prints the total running time of the query

    Time is in seconds, and it's decimal precision is determined
    by the PERFORMANCE_PRECISION constant.
    """
    total_time = str(round(end - start, PERFORMANCE_PRECISION))
    print 'total time: {} seconds'.format(total_time)


def get_query_from_yaml(config_path):
    """Creates a Query object from a yaml file found in config_path.

    The Query object is created from the configuration found in the yaml file.
    Filters objects are created from the yaml file aswell and are attached
    to the Query.
    :param config_path: Path to the configuration yaml file.
    :return: A Query object along with the filters in the file, if found.
    """
    try:
        with open(config_path) as config_file:
            yaml_contents = yaml.load(config_file)

    except IOError:
        sys.exit('The config.yaml path you provided, `{0}`, does not '
                 'lead to an existing file.'.format(config_path))

    yaml_config = yaml_contents['query_config']
    yaml_filters = yaml_contents['filters']

    qc = QueryConfig.from_yaml(yaml_config)
    filters = [Filter.from_yaml(yaml_filter) for yaml_filter in yaml_filters]

    query = Query.from_config(qc)
    query.attach_filters(filters)

    return query


def get_query_from_args(args):
    """Creates a Query object from the CLI arguments.

    Filter objects are created from the CLI argument and attached to the
    Query object.
    :param args: CLI arguments
    :return: A Query object along with the created filters, if found.
    """
    qc = QueryConfig.from_args(args)
    filters = get_filters_from_args(args)

    query = Query.from_config(qc)
    query.attach_filters(filters)

    return query


def main():
    # Save the start time
    start = time.time()
    args = parse_arguments()
    # Make sure the Github environment variables are set
    enforce_github_env_variables()

    if args.config_path:
        # Get the Query from yaml if a config_path argument is given
        query = get_query_from_yaml(args.config_path)
    else:
        # Get the Query from the CLI arguments if no config_path is argument
        # is found
        query = get_query_from_args(args)

    query.query()
    query.output()
    # Print how long was the whole operation
    print_performance(start, time.time())


if __name__ == '__main__':
    main()
