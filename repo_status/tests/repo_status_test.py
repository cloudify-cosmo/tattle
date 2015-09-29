import unittest

from mock import MagicMock

from repo_status import engine
from repo_status import model



class TestRepoMethods(unittest.TestCase):

    # the method get_json_repos(...) get a json from GitHub. so how do test this method?

    def test_parse_json_repos_with_an_empty_json(self):

        empty_json = '{}'
        expected_result = []
        original = engine.Engine()

        self.assertEqual(original.parse_json_repos(empty_json), expected_result)

    def test_parse_json_repos_with_a_simple_json(self):

        json_repos = '[{"name":"gs-ui-infra"}, {"name":"getcloudify.org"}]'
        expected_result = [model.Repo('gs-ui-infra'), model.Repo('getcloudify.org')]
        original = engine.Engine()

        self.assertEqual(original.parse_json_repos(json_repos), expected_result)

    def test_that_get_repos_is_sorting_the_repos(self):

        mocked_method = MagicMock(name='get_json_repos_mock')
        mocked_method.return_value = '[{"name":"gs-ui-infra"}, {"name":"getcloudify.org"}]'

        original = engine.Engine()
        original.get_json_repos = mocked_method

        expected_result = [model.Repo('getcloudify.org'), model.Repo('gs-ui-infra')]

        self.assertEqual(original.get_repos(), expected_result)

    # how about also testing that the get_repos() calls get_json_repos() and parse_json_repos()?


class TestBranchMethods(unittest.TestCase):

    # the method get_json_branches(...) get a json from GitHub. so how do test this method?
    # change the tests to handle the new containing repo attribute

    def test_parse_json_branches_with_an_empty_json(self):

        empty_json = '{}'
        expected_result = []
        original = engine.Engine()
        sample_repo = model.Repo('sample repo')
        self.assertEqual(original.parse_json_branches(empty_json, sample_repo), expected_result)

    def test_parse_json_branches_with_a_simple_json(self):

        json_branches = '[{"name":"delete-dead-link-guide"}, {"name":"CFY-3529-Examples-Section"}]'

        expected_result = [model.Branch('delete-dead-link-guide'),
                           model.Branch('CFY-3529-Examples-Section')]
        original = engine.Engine()

        self.assertEqual(original.parse_json_branches(json_branches), expected_result)

    # test that parse_branches is assigning each branch a containing repo

    def test_parse_branches_for_assigning_containing_repo(self):
        sample_repo = model.Repo('sample repo')
        json_branches = '[{"name":"CFY-3529-Examples-Section"}]'
        branches = engine.Engine().parse_json_branches(json_branches, sample_repo)
        self.assertEqual(sample_repo, branches[0].containing_repo)


    def test_that_get_branches_is_sorting_the_branches(self):

        mocked_method = MagicMock(name='get_json_branches_mock')
        mocked_method.return_value = '[{"name":"delete-dead-link-guide"},' \
                                     '{"name":"CFY-3529-Examples-Section"}]'

        original = engine.Engine()
        original.get_json_branches = mocked_method

        expected_result = [model.Branch('CFY-3529-Examples-Section'),
                           model.Branch('delete-dead-link-guide')]

        self.assertEqual(original.get_branches(), expected_result)


class TestSurplusBranches(unittest.TestCase):
    pass







if __name__ == '__main__':
    unittest.main()