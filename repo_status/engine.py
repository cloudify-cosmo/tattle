import argparse
from repo_status.model import USE_CACHE_MODE
from repo_status.model import UP_TO_DATE_MODE
from repo_status.model import BranchQueryCfy
from repo_status.model import BranchQuerySurplus
from repo_status.model import QueryConfig
import os
import sys
import tempfile
import time

_ARGUMENT_PARSER_DESCRIPTION = \
    ('Get in-depth information about the status '
     'of your GitHub branches')
_SURPLUS_BRANCHES_HELP_TEXT = \
    'display the surplus branches of cloudify-cosmo'
_CFY_BRANCHES_HELP_TEXT = \
    'display all the CFY branches whose JIRA issue status' \
    ' is either \'closed\' or \'resolved\''
_CACHE_PATH_HELP_TEXT = \
    'supply a custom path for the cache files\n. ' \
    'if a custom path is no\t supplied, ' \
    'the files will be stored under your home directory.'
_MAX_THREADS_HELP_TEXT = \
    'maximal number of threads used for retrieving branch data.\n' \
    'if not specified, the program will use as many threads as it needs'

SURPLUS_BRANCHES_COMMAND_NAME = '--surplus-branches'
CFY_BRANCHES_COMMAND_NAME = '--cfy-branches'
CACHE_PATH_COMMAND_NAME = '--cache-path'
MAX_THREADS_COMMAND_NAME = '--max-threads'

SURPLUS_BRANCHES_PARSE_NAME = 'surplus_branches'
CFY_BRANCHES_PARSE_NAME = 'cfy_branches'
CACHE_PATH_PARSE_NAME = 'cache_path'

CACHE_DOESNT_EXIST = 'The cache path you specified doesn\'t exist, ' \
                     'or it doesn\'t contain the required cache files.'
CACHE_PATH_INVALID = 'The cache path you supplied is illegal or restricted.'

RESOURCES_FOLDER_PATH = \
    os.path.join(tempfile.gettempdir(),
                 'cloudify-repo-status/resources/')


def parse_arguments():

    parser = argparse.ArgumentParser(
        description=_ARGUMENT_PARSER_DESCRIPTION)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-s', SURPLUS_BRANCHES_COMMAND_NAME,
                       type=str,
                       nargs='?',
                       choices=[USE_CACHE_MODE,
                                UP_TO_DATE_MODE],
                       const=UP_TO_DATE_MODE,
                       default=None,
                       help=_SURPLUS_BRANCHES_HELP_TEXT)

    group.add_argument('-c', CFY_BRANCHES_COMMAND_NAME,
                       type=str,
                       nargs='?',
                       choices=[USE_CACHE_MODE,
                                UP_TO_DATE_MODE],
                       const=UP_TO_DATE_MODE,
                       default=None,
                       help=_CFY_BRANCHES_HELP_TEXT)

    cache_action = \
        parser.add_argument('-p', CACHE_PATH_COMMAND_NAME,
                            type=str,
                            default=None,
                            help=_CACHE_PATH_HELP_TEXT,
                            )

    parser.add_argument('-t', MAX_THREADS_COMMAND_NAME,
                        type=int,
                        default=QueryConfig.NO_THREAD_LIMIT,
                        help=_MAX_THREADS_HELP_TEXT)

    args = parser.parse_args()

    enforce_caching_with_query(parser, args, cache_action)
    return args, parser


def determine_if_cache_exists(command_name, user_resource_path):

    filename = BranchQuerySurplus.FILENAME \
        if command_name == SURPLUS_BRANCHES_PARSE_NAME \
        else BranchQueryCfy.FILENAME
    filepath = os.path.join(user_resource_path, filename)

    if not os.path.isdir(user_resource_path) or not os.path.isfile(filepath):
        sys.exit(CACHE_DOESNT_EXIST)


def determine_if_cache_path_is_legal(user_resource_path):

    if not os.path.exists(user_resource_path):
        try:
            os.makedirs(user_resource_path)
        except (IOError, OSError):
            sys.exit(CACHE_PATH_INVALID)


def determine_resources_path(args):

    d = vars(args)
    if d[CACHE_PATH_PARSE_NAME] is None:
        if not os.path.exists(RESOURCES_FOLDER_PATH):
            os.makedirs(RESOURCES_FOLDER_PATH)
        return RESOURCES_FOLDER_PATH

    user_resource_path = os.path.join(os.path.expanduser('~'),
                                      d[CACHE_PATH_PARSE_NAME])
    command_name = SURPLUS_BRANCHES_PARSE_NAME \
        if SURPLUS_BRANCHES_PARSE_NAME in d else CFY_BRANCHES_PARSE_NAME

    # if the user wishes to load the data from a predefined existing cache,
    # then we need to make sure that it exists.
    if USE_CACHE_MODE in d.values():
        determine_if_cache_exists(command_name, user_resource_path)

    # if the user wishes to use a custom path to save his cache in,
    # this path doesn't have to exist right now, but it must be legal.
    else:
        determine_if_cache_path_is_legal(user_resource_path)

    return os.path.join(os.path.expanduser('~'), user_resource_path)


def enforce_caching_with_query(parser, args, cache_action):

    if args.cache_path and not args.surplus_branches \
            and not args.cfy_branches:
        parser.error('{0} must be given with --cfy-branches or '
                     '--surplus-branches'
                     .format(' or '.join(cache_action.option_strings)))


def main():

    args, parser = parse_arguments()
    resources_path = determine_resources_path(args)

    if args.surplus_branches is not None:

        mode = args.surplus_branches,
        filename = BranchQuerySurplus.FILENAME
        query = BranchQuerySurplus()

    elif args.cfy_branches is not None:

        mode = args.cfy_branches
        filename = BranchQueryCfy.FILENAME
        query = BranchQueryCfy()

    else:
        parser.print_usage(file=None)
        sys.exit()

    query.config = QueryConfig(resources_path,
                               mode,
                               filename,
                               max_threads=args.max_threads,
                               )
    query.process()


if __name__ == '__main__':
    main()
