import os
import tempfile

PROJECT_NAME = 'Tattle'


class QueryConfig(object):

    DATA_TYPE = 'data_type'
    MAX_THREADS = 'max_threads'
    NO_THREAD_LIMIT = -1
    GITHUB_ORG_NAME = 'github_org_name'
    OUTPUT_PATH = 'output_path'
    DEFAULT_OUTPUT_FILE_NAME = 'report.json'
    DEFAULT_OUTPUT_RELATIVE_PATH = os.path.join(PROJECT_NAME,
                                                DEFAULT_OUTPUT_FILE_NAME)
    DEFAULT_OUTPUT_PATH = os.path.join(tempfile.gettempdir(),
                                       DEFAULT_OUTPUT_RELATIVE_PATH)

    def __init__(self,
                 data_type,
                 max_threads,
                 github_org_name,
                 output_path,
                 filters):

        self.data_type = data_type
        self.max_threads = max_threads
        self.github_org_name = github_org_name
        self.output_path = output_path
        self.filters = filters

    @classmethod
    def from_yaml(cls, yaml_qc):

        data_type = yaml_qc.get(cls.DATA_TYPE)
        max_threads = yaml_qc.get(cls.MAX_THREADS, cls.NO_THREAD_LIMIT)
        github_org_name = yaml_qc.get(cls.GITHUB_ORG_NAME)
        output_path = yaml_qc.get(cls.OUTPUT_PATH, cls.DEFAULT_OUTPUT_PATH)
        # filters = [FilterFactory(yaml_filter) for yaml_filter in aml_qc.get('filters')]







    # the former determine_max_number_of_threads will now
    # be a property named num_of_threads that does the
    # above calculation
        