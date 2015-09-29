import argparse
import model
import os
import time
import sys


class Engine(object):

    _ARGUMENT_PARSER_DESCRIPTION = \
        ('Get in-depth information about the status '
         'of your GitHub branches')
    _SURPLUS_BRANCHES_HELP_TEXT = \
        'display the surplus branches of cloudify-cosmo'
    _CFY_BRANCHES_HELP_TEXT = \
        'display all the CFY branches whose JIRA issue status' \
        ' is either \'closed\' or \'resolved\''
    _CACHE_PATH_HELP_TEXT =\
        'supply a custom path for the cache files. ' \
        'if a custom path is not supplied, ' \
        'the files will be stored under your home directory.'
    _USE_CACHE_MODE = 'use-cache'
    _UP_TO_DATE_MODE = 'up-to-date'
    _SURPLUS_BRANCHES_COMMAND_NAME = '--surplus-branches'
    _CFY_BRANCHES_COMMAND_NAME = '--cfy-branches'
    _CACHE_PATH_COMMAND_NAME = '--cache-path'

    # authenticating is easy. simply use this example:
    # r = requests.get(URL, auth=(username, password))
    # I'm not implementing this globally right now because I need to find out
    # how to store the password in a secure way (i.e not in code)

    def process_command(self, mode, query):

        start_time = time.time()

        if mode == Engine._UP_TO_DATE_MODE:
            query.update_cache()

        branches = query.load_branches(query.
                                       query_config.
                                       branches_file_path)
        query_branches = filter(query.branch_filter, branches)
        query.output(query_branches)

        end_time = time.time()
        total_time_in_seconds = (end_time - start_time)

        self.print_performance(query.DESCRIPTION, total_time_in_seconds)

    def print_performance(self, description, seconds):

        print '\n'
        print 'action:     ' + description
        print 'total time: ' + str(seconds * 1000) + 'ms\n\n'

    def parse_arguments(self):

        parser = argparse.ArgumentParser(
            description=Engine._ARGUMENT_PARSER_DESCRIPTION)
        group = parser.add_mutually_exclusive_group()
        surplus_action = \
            group.add_argument('-s', Engine._SURPLUS_BRANCHES_COMMAND_NAME,
                               type=str,
                               nargs='?',
                               choices=[Engine._USE_CACHE_MODE,
                                        Engine._UP_TO_DATE_MODE],
                               const=Engine._UP_TO_DATE_MODE,
                               default=None,
                               help=Engine._SURPLUS_BRANCHES_HELP_TEXT)

        cfy_action = \
            group.add_argument('-c', Engine._CFY_BRANCHES_COMMAND_NAME,
                               type=str,
                               nargs='?',
                               choices=[Engine._USE_CACHE_MODE,
                                        Engine._UP_TO_DATE_MODE],
                               const=Engine._UP_TO_DATE_MODE,
                               help=Engine._CFY_BRANCHES_HELP_TEXT)

        cache_action = \
            parser.add_argument('-p', Engine._CACHE_PATH_COMMAND_NAME,
                                type=str,
                                nargs=1,
                                help=Engine._CACHE_PATH_HELP_TEXT,
                                )
        given_args = set(sys.argv)
        branch_actions_option_strings = (set(surplus_action.option_strings) |
                                         set(cfy_action.option_strings)
                                         )
        if (given_args & set(cache_action.option_strings)) and \
           (not given_args & branch_actions_option_strings):
            parser.error(' or '.join(cache_action.option_strings) +
                         ' must be given with ' +
                         ' or '.join(branch_actions_option_strings))

        args = parser.parse_args()
        return args, parser


def main():

    engine = Engine()
    args, parser = engine.parse_arguments()

    query_config = model.QueryConfig()
    if args.cache_path:
        if not os.path.isdir(args.cache_path):
            print 'The cache directory you specified doesn\'t exist.' \
                  'using your home directory as a default.'
        else:
            query_config = model.QueryConfig(args.cache_path)

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
