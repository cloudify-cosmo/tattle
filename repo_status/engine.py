import argparse
import model
import os
import time
import sys

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
    'if a custom path is not supplied, ' \
    'the files will be stored under your home directory.'
_MAX_THREADS_HELP_TEXT = \
    'maximal number of threads used for retrieving branch data.\n' \
    'if not specified, the program will use as many threads as it needs'

_SURPLUS_BRANCHES_COMMAND_NAME = '--surplus-branches'
_CFY_BRANCHES_COMMAND_NAME = '--cfy-branches'
_CACHE_PATH_COMMAND_NAME = '--cache-path'
_MAX_THREADS_COMMAND_NAME = '--max-threads'

_SURPLUS_BRANCHES_PARSE_NAME = 'surplus_branches'
_CFY_BRANCHES_PARSE_NAME = 'cfy_branches'
_CACHE_PATH_PARSE_NAME = 'cache_path'

_USE_CACHE_MODE = 'use-cache'
_UP_TO_DATE_MODE = 'up-to-date'


CACHE_DOESNT_EXIST = 'The cache path you specified doesn\'t exist, ' \
                     'or it doesn\'t contain the required cache files.'
CACHE_PATH_INVALID = 'The cache path you supplied is illegal or restricted.'

RESOURCES_FOLDER_PATH = \
    os.path.join(os.path.expanduser('~'),
                 '.cloudify-repo-status/resources/')


class Engine(object):

    @staticmethod
    def determine_if_cache_exists(command_name, user_resource_path):

        try:
            with open(user_resource_path, 'r'), \
                open(os.path.join(user_resource_path,
                                  model.BRANCHES_FILENAME), 'r'):
                if command_name == _CFY_BRANCHES_PARSE_NAME:
                    with open(os.path.join(user_resource_path,
                                           model.ISSUES_FILENAME), 'r'):
                        pass
        except IOError:
            sys.exit(CACHE_DOESNT_EXIST)

    @staticmethod
    def determine_if_cache_path_is_legal(user_resource_path):

        if not os.path.exists(user_resource_path):
            try:
                os.makedirs(user_resource_path)
            except (IOError, OSError):
                sys.exit(CACHE_PATH_INVALID)

    @staticmethod
    def determine_resources_path(args):

        d = vars(args)
        if d[_CACHE_PATH_PARSE_NAME] is None:
            return RESOURCES_FOLDER_PATH

        user_resource_path = os.path.join(os.path.expanduser('~'),
                                          d[_CACHE_PATH_PARSE_NAME])
        command_name = _SURPLUS_BRANCHES_PARSE_NAME \
            if _SURPLUS_BRANCHES_PARSE_NAME in d else _CFY_BRANCHES_PARSE_NAME

        # if the user wishes to load the data from a predefined existing cache,
        # then we need to make sure that it exists.
        if _USE_CACHE_MODE in d.values():
            Engine.determine_if_cache_exists(command_name, user_resource_path)

        # if the user wishes to use a custom path to save his cache in,
        # this path need not exist right now, but it must be legal.
        else:
            Engine.determine_if_cache_path_is_legal(user_resource_path)

        return os.path.join(os.path.expanduser('~'), user_resource_path)

    @staticmethod
    def print_performance(description, seconds):

        print '\n'
        print 'action: {}'.format(description)
        print 'total time: {}{}'.format(str(seconds * 1000), 'ms\n\n')

    def process_command(self, mode, query):

        start_time = time.time()

        if mode == _UP_TO_DATE_MODE:
            branches = query.get_org_branches()
            query_branches = query.filter_branches(branches)
            query.add_commiters_and_dates(query_branches)
            query.update_cache(query_branches)
        else:
            query_branches = query.load_branches()

        query.output(query_branches)

        end_time = time.time()
        total_time_in_seconds = (end_time - start_time)

        Engine.print_performance(query.DESCRIPTION, total_time_in_seconds)

    @staticmethod
    def enforce_caching_with_query(surplus_action, cfy_action, cache_action,
                                   parser):
        """
        Makes sure that if the user specified the cache-path flag,
        She also specified a query (surplus of cfy)
        """
        given_args = set(sys.argv)

        branch_queries_strings = set()
        for s in surplus_action.option_strings + cfy_action.option_strings:
            branch_queries_strings.add(s)
            branch_queries_strings.add(s + '=' + _USE_CACHE_MODE)
            branch_queries_strings.add(s + '=' + _UP_TO_DATE_MODE)
            branch_queries_strings.add(s + ' ' + _USE_CACHE_MODE)
            branch_queries_strings.add(s + ' ' + _UP_TO_DATE_MODE)

        caching_cond = given_args & set(cache_action.option_strings)
        query_cond = not given_args & branch_queries_strings

        if caching_cond and query_cond:
            parser.error(' or '.join(cache_action.option_strings) +
                         ' must be given with ' +
                         ' or '.join(branch_queries_strings))

    def parse_arguments(self):

        parser = argparse.ArgumentParser(
            description=_ARGUMENT_PARSER_DESCRIPTION)
        group = parser.add_mutually_exclusive_group()
        surplus_action = \
            group.add_argument('-s', _SURPLUS_BRANCHES_COMMAND_NAME,
                               type=str,
                               nargs='?',
                               choices=[_USE_CACHE_MODE,
                                        _UP_TO_DATE_MODE],
                               const=_UP_TO_DATE_MODE,
                               default=None,
                               help=_SURPLUS_BRANCHES_HELP_TEXT)

        cfy_action = \
            group.add_argument('-c', _CFY_BRANCHES_COMMAND_NAME,
                               type=str,
                               nargs='?',
                               choices=[_USE_CACHE_MODE,
                                        _UP_TO_DATE_MODE],
                               const=_UP_TO_DATE_MODE,
                               help=_CFY_BRANCHES_HELP_TEXT)

        cache_action = \
            parser.add_argument('-p', _CACHE_PATH_COMMAND_NAME,
                                type=str,
                                help=_CACHE_PATH_HELP_TEXT,
                                )

        parser.add_argument('-t', _MAX_THREADS_COMMAND_NAME,
                            type=int,
                            default=model.QueryConfig.NO_THREAD_LIMIT,
                            help=_MAX_THREADS_HELP_TEXT)

        Engine.enforce_caching_with_query(surplus_action,
                                          cfy_action,
                                          cache_action,
                                          parser)
        args = parser.parse_args()
        return args, parser


def main():

    engine = Engine()
    args, parser = engine.parse_arguments()
    resources_path = engine.determine_resources_path(args)
    query_config = model.QueryConfig(resources_path, args.max_threads)

    if args.surplus_branches:
        engine.process_command(args.surplus_branches,
                               model.BranchQuerySurplus(query_config))
    elif args.cfy_branches:
        engine.process_command(args.cfy_branches,
                               model.BranchQueryCfy(query_config))
    else:
        parser.print_usage(file=None)

if __name__ == '__main__':
    main()
