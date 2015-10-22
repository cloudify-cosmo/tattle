import argparse
from repo_status import model
import os
import sys
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

USE_CACHE_MODE = 'use-cache'
UP_TO_DATE_MODE = 'up-to-date'

CACHE_DOESNT_EXIST = 'The cache path you specified doesn\'t exist, ' \
                     'or it doesn\'t contain the required cache files.'
CACHE_PATH_INVALID = 'The cache path you supplied is illegal or restricted.'

RESOURCES_FOLDER_PATH = \
    os.path.join(os.path.expanduser('~'),
                 '.cloudify-repo-status/resources/')


def parse_arguments():

    parser = argparse.ArgumentParser(
        description=_ARGUMENT_PARSER_DESCRIPTION)
    group = parser.add_mutually_exclusive_group()
    surplus_action = \
        group.add_argument('-s', SURPLUS_BRANCHES_COMMAND_NAME,
                           type=str,
                           nargs='?',
                           choices=[USE_CACHE_MODE,
                                    UP_TO_DATE_MODE],
                           const=UP_TO_DATE_MODE,
                           default=None,
                           help=_SURPLUS_BRANCHES_HELP_TEXT)

    cfy_action = \
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
                        default=model.QueryConfig.NO_THREAD_LIMIT,
                        help=_MAX_THREADS_HELP_TEXT)

    args = parser.parse_args()

    enforce_caching_with_query(parser, args, cache_action)
    return args, parser


def determine_if_cache_exists(command_name, user_resource_path):

    try:
        with open(user_resource_path, 'r'):
            if command_name == SURPLUS_BRANCHES_PARSE_NAME:
                with open(os.path.join(user_resource_path,
                                       model
                                       .BranchQuerySurplus
                                       .FILENAME), 'r'):
                    pass
            if command_name == CFY_BRANCHES_PARSE_NAME:
                with open(os.path.join(user_resource_path,
                                       model
                                       .BranchQueryCfy
                                       .FILENAME), 'r'):
                    pass

    except IOError:
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

def process_command(mode, query):

    query.performance.start = time.time()

    if mode == UP_TO_DATE_MODE:
        branches = query.get_org_branches()
        query_branches = query.filter_branches(branches)
        query.add_committers_and_dates(query_branches)
        query.update_cache(query_branches)

    else:
        query_branches = query.load_branches()

    query.output(query_branches)

    query.performance.end = time.time()
    query.print_performance()


def main():

    args, parser = parse_arguments()
    resources_path = determine_resources_path(args)
    query_config = model.QueryConfig(resources_path, args.max_threads)

    if args.surplus_branches:
        process_command(args.surplus_branches,
                        model.BranchQuerySurplus(query_config))
    elif args.cfy_branches:
        process_command(args.cfy_branches,
                        model.BranchQueryCfy(query_config))
    else:
        parser.print_usage(file=None)

if __name__ == '__main__':
    main()
