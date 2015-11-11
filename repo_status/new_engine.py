import argparse
import os
import yaml
import sys

from repo_status.new_model import QueryConfig
from repo_status.new_model import Filter


GITHUB_USER = 'GITHUB_USER'
GITHUB_PASS = 'GITHUB_PASS'
CONFIG_PATH_COMMAND_NAME = '--config-path'
CONFIG_PATH_HELP_TEXT = 'a path to a YAML configuration file'

GITHUB_ENV_VARS_DONT_EXIST = 'GitHub authentication environment variables' \
                             ' do not exist.\nPlease define them: ' \
                             '[GITHUB_USER], [GITHUB_PASS], and try again.'

ARGUMENT_PARSER_DESCRIPTION = 'Perform simple queries on your GitHub branches'


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


def main():

    # enforce_github_env_variables()
    args = parse_arguments()
    try:
        with open(args.config_path) as config_file:
            yaml_config = yaml.load(config_file['query_config'])
            yaml_filters = yaml.load(config_file['filters'])

    except IOError as error:
        sys.exit(error)

    qc = QueryConfig.from_yaml(yaml_config)
    filters = [Filter.create_from_yaml(yaml_filter)
               for yaml_filter in yaml_filters]

    # create a xQuery with a factory
    # according to the data_type field of query_config.
    # maybe give the factory the whole QC object,
    # and inside the factory we will extract the data_type
    # and return the corresponding xQuery that includes as a attribute
    # the QC object that was given to the factory

if __name__ == '__main__':
    main()
