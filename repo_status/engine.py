# import argparse
# from repo_status.model import GITHUB_PASS
# from repo_status.model import GITHUB_USER
# from repo_status.model import UP_TO_DATE_MODE
# from repo_status.model import USE_CACHE_MODE
# from repo_status.model import BranchQueryStale
# from repo_status.model import BranchQuerySurplus
# from repo_status.model import TagQuery


# import tempfile
#
# ARGUMENT_PARSER_DESCRIPTION = \
#     ('Get in-depth information about the status '
#      'of your GitHub branches')
# SURPLUS_BRANCHES_HELP_TEXT = \
#     'display the surplus branches of cloudify-cosmo'
# STALE_BRANCHES_HELP_TEXT = \
#     'display all the CFY branches whose JIRA issue status' \
#     ' is either \'closed\' or \'resolved\''
# TAGS_HELP_TEXT = 'display all the tags that don\'t follow ' \
#                  'the tag-naming convention'
# CACHE_PATH_HELP_TEXT = \
#     'supply a custom path for the cache files\n. ' \
#     'if a custom path is no\t supplied, ' \
#     'the files will be stored under your home directory.'
# MAX_THREADS_HELP_TEXT = \
#     'maximal number of threads used for retrieving branch data.\n' \
#     'if not specified, the program will use as many threads as it needs'
#
# SURPLUS_BRANCHES_COMMAND_NAME = '--surplus-branches'
# STALE_BRANCHES_COMMAND_NAME = '--stale-branches'
# TAGS_COMMAND_NAME = '--tags'
# CACHE_PATH_COMMAND_NAME = '--cache-path'
# MAX_THREADS_COMMAND_NAME = '--max-threads'
#
# SURPLUS_BRANCHES_PARSE_NAME = 'surplus_branches'
# STALE_BRANCHES_PARSE_NAME = 'stale_branches'
# TAGS_PARSE_NAME = 'tags'
# CACHE_PATH_PARSE_NAME = 'cache_path'
#
# CACHE_DOESNT_EXIST = 'The cache path you specified doesn\'t exist, ' \
#                      'or it doesn\'t contain the required cache files.'
# CACHE_PATH_INVALID = 'The cache path you supplied is illegal or restricted.'
# RESOURCES_FOLDER_PATH = \
#     os.path.join(tempfile.gettempdir(),
#                  'cloudify-repo-status/resources/')
#
#
# def parse_arguments():
#
#     parser = argparse.ArgumentParser(
#         description=ARGUMENT_PARSER_DESCRIPTION)
#     group = parser.add_mutually_exclusive_group()
#     group.add_argument('-s', SURPLUS_BRANCHES_COMMAND_NAME,
#                        type=str,
#                        nargs='?',
#                        choices=[USE_CACHE_MODE,
#                                 UP_TO_DATE_MODE],
#                        const=UP_TO_DATE_MODE,
#                        default=None,
#                        help=SURPLUS_BRANCHES_HELP_TEXT)
#
#     group.add_argument('-c', STALE_BRANCHES_COMMAND_NAME,
#                        type=str,
#                        nargs='?',
#                        choices=[USE_CACHE_MODE,
#                                 UP_TO_DATE_MODE],
#                        const=UP_TO_DATE_MODE,
#                        default=None,
#                        help=STALE_BRANCHES_HELP_TEXT)
#
#     group.add_argument('-t', TAGS_COMMAND_NAME,
#                        type=str,
#                        nargs='?',
#                        choices=[USE_CACHE_MODE,
#                                 UP_TO_DATE_MODE],
#                        const=UP_TO_DATE_MODE,
#                        default=None,
#                        help=TAGS_HELP_TEXT
#                        )
#
#     cache_action = \
#         parser.add_argument('-p', CACHE_PATH_COMMAND_NAME,
#                             type=str,
#                             default=None,
#                             help=CACHE_PATH_HELP_TEXT,
#                             )
#
#     parser.add_argument('-m', MAX_THREADS_COMMAND_NAME,
#                         type=int,
#                         default=QueryConfig.NO_THREAD_LIMIT,
#                         help=MAX_THREADS_HELP_TEXT)
#
#     args = parser.parse_args()
#
#     enforce_caching_with_query(parser, args, cache_action)
#     return args, parser
#
#
# def determine_if_cache_exists(command_name, user_resource_path):
#
#     if command_name == SURPLUS_BRANCHES_PARSE_NAME:
#         filename = BranchQuerySurplus.FILENAME
#     elif command_name == STALE_BRANCHES_PARSE_NAME:
#         filename = BranchQuerySurplus.FILENAME
#     else:  # command_name == TAGS_PARSE_NAME:
#         filename = TagQuery.FILENAME
#
#     filepath = os.path.join(user_resource_path, filename)
#
#     if not os.path.isdir(user_resource_path) or not os.path.isfile(filepath):
#         sys.exit(CACHE_DOESNT_EXIST)
#
#
# def determine_if_cache_path_is_legal(user_resource_path):
#
#     if not os.path.exists(user_resource_path):
#         try:
#             os.makedirs(user_resource_path)
#         except (IOError, OSError):
#             sys.exit(CACHE_PATH_INVALID)
#
#
# def determine_resources_path(args):
#
#     d = vars(args)
#     if d[CACHE_PATH_PARSE_NAME] is None:
#         if not os.path.exists(RESOURCES_FOLDER_PATH):
#             os.makedirs(RESOURCES_FOLDER_PATH)
#         return RESOURCES_FOLDER_PATH
#
#     user_resource_path = os.path.join(os.path.expanduser('~'),
#                                       d[CACHE_PATH_PARSE_NAME])
#     command_name = SURPLUS_BRANCHES_PARSE_NAME \
#         if SURPLUS_BRANCHES_PARSE_NAME in d else STALE_BRANCHES_PARSE_NAME
#
#     # if the user wishes to load the data from a predefined existing cache,
#     # then we need to make sure that it exists.
#     if USE_CACHE_MODE in d.values():
#         determine_if_cache_exists(command_name, user_resource_path)
#
#     # if the user wishes to use a custom path to save his cache in,
#     # this path doesn't have to exist right now, but it must be legal.
#     else:
#         determine_if_cache_path_is_legal(user_resource_path)
#
#     return os.path.join(os.path.expanduser('~'), user_resource_path)
#
#
#
#
# def enforce_caching_with_query(parser, args, cache_action):
#
#     if args.cache_path and not args.surplus_branches \
#             and not args.stale_branches and not args.tags:
#         parser.error('{0} must be given with --stale-branches or '
#                      '--surplus-branches or --tags'
#                      .format(' or '.join(cache_action.option_strings)))
#
#
# def main():
#
#     enforce_github_env_variables()
#
#     args, parser = parse_arguments()
#     resources_path = determine_resources_path(args)
#
#     if args.surplus_branches is not None:
#
#         mode = args.surplus_branches
#         filename = BranchQuerySurplus.FILENAME
#         query = BranchQuerySurplus()
#
#     elif args.stale_branches is not None:
#
#         mode = args.stale_branches
#         filename = BranchQueryStale.FILENAME
#         query = BranchQueryStale()
#
#     elif args.tags is not None:
#
#         mode = args.tags
#         filename = TagQuery.FILENAME
#         query = TagQuery()
#
#     else:
#         parser.print_usage(file=None)
#         sys.exit()
#
#     query.config = QueryConfig(resources_path,
#                                mode,
#                                filename,
#                                max_threads=args.max_threads,
#                                )
#
#     with query.performance.total:
#         query.process()
#     query.output()
#     query.print_performance()
#
#
import argparse
import os
import tempfile
import yaml
import sys

from repo_status.model import QueryConfig
from repo_status.model import NameFilter

GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
CONFIG_PATH_COMMAND_NAME = '--config-path'
CONFIG_PATH_HELP_TEXT = 'a path to a YAML configuration file'

GITHUB_ENV_VARS_DONT_EXIST = 'GitHub authentication environment variables' \
                             ' do not exist.\nPlease define them: ' \
                             '[GITHUB_USER], [GITHUB_PASS], and try again.'

ARGUMENT_PARSER_DESCRIPTION = 'Perform simple queries on your GitHub branches'

ORG_NAME = 'org_name'
MAX_THREADS = 'max_threads'
OUTPUT_PATH = 'output path'
DEFAULT_OUTPUT_PATH = os.path.join(tempfile.gettempdir(),
                                  'cloudify-repo-status/report.json')
NAME_FILTER = 'name_filter'
ISSUE_FILTER = 'issue_filter/'
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
            qc = QueryConfig()
            qc.org_name = yaml_config.get(ORG_NAME)
            qc.max_threads = yaml_config.get(MAX_THREADS, qc.NO_THREAD_LIMIT)
            qc.output_path = yaml_config.get(OUTPUT_PATH, DEFAULT_OUTPUT_PATH)
            qc.name_filter = NameFilter.from_yaml(
                yaml_config.get(NAME_FILTER, None))
            # qc.issue_filter = IssueFilter.from_yaml(
            #     yaml_config.get(ISSUE_FILTER, None))
            # for each of these fields, fill qc will a value. if a field doesn't exist, consider using a default value:
            # org_name, maximal_number_of_threads, output_file_path, name_filters,
            # issue_filters {branch_target_name, branch_to_issue_transform: {from, to}, statuses},
            # cache_path???
            # return qc
            pass

    except IOError as error:
        sys.exit(error)


def main():

    # enforce_github_env_variables()
    args = parse_arguments()

    # validate_config_path(args)
    # put that inside 'create_config'. no need to open the file twice.
    # or even don't make this test without 'dedicating' a function to it.
    config = create_query_config(args)
    # query = Query()
    # query.config = create_query_config(args.config_path)
    # query.procces()





if __name__ == '__main__':
   main()


