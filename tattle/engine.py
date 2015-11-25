import argparse
import os
import time
import yaml
import sys

from tattle.model import QueryConfig
from tattle.model import Query
from tattle.model import Filter


GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
CONFIG_PATH_COMMAND_NAME = '--config-path'
CONFIG_PATH_HELP_TEXT = 'a path to a YAML configuration file'

GITHUB_ENV_VARS_DONT_EXIST = 'GitHub authentication environment variables' \
                             ' do not exist.\nPlease define them: ' \
                             '[GITHUB_USER], [GITHUB_PASS], and try again.'

ARGUMENT_PARSER_DESCRIPTION = 'Perform simple queries on your GitHub branches'

PERFORMANCE_PRECISION = 3


def enforce_github_env_variables():

    if not os.environ[GITHUB_USER] or not os.environ[GITHUB_PASS]:

        raise KeyError(GITHUB_ENV_VARS_DONT_EXIST)


def parse_arguments():

    parser = argparse.ArgumentParser(description=ARGUMENT_PARSER_DESCRIPTION)
    parser.add_argument(CONFIG_PATH_COMMAND_NAME, '-c',
                        metavar='<PATH_TO_CONFIG>',
                        type=str,
                        help=CONFIG_PATH_HELP_TEXT,
                        required=True)

    return parser.parse_args()


def print_performance(start, end):

    total_time = str(round(end - start, PERFORMANCE_PRECISION))
    print 'total time: {} seconds'.format(total_time)


def main():

    start = time.time()
    enforce_github_env_variables()
    args = parse_arguments()

    try:
        with open(args.config_path) as config_file:
            yaml_contents = yaml.load(config_file)
    except IOError:
        sys.exit('The config.yaml path you provided, `{0}`, does not '
                 'lead to an existing file.'.format(args.config_path))

    yaml_config = yaml_contents['query_config']
    yaml_filters = yaml_contents['filters']

    qc = QueryConfig.from_yaml(yaml_config)
    filters = [Filter.from_yaml(yaml_filter) for yaml_filter in yaml_filters]

    query = Query.from_config(qc)
    query.attach_filters(filters)
    query.query()
    query.output()
    print_performance(start, time.time())


if __name__ == '__main__':
    main()
