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
                        metavar='<CONFIG_FILE>',

                        help=CONFIG_PATH_HELP_TEXT,
                        required=True)

    return parser.parse_args()


def print_performance(start, end):
    """ Prints the total running time of the query

    Time is in seconds, and it's decimal precision is determined
    by the PERFORMANCE_PRECISION constant.
    """
    total_time = str(round(end - start, PERFORMANCE_PRECISION))
    print 'total time: {} seconds'.format(total_time)


def main():

    start = time.time()
    args = parse_arguments()
    enforce_github_env_variables()

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
