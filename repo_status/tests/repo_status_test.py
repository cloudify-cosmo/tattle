from repo_status.model import Branch
from repo_status.model import Issue
from repo_status.model import Repo

from testtools import TestCase

### repo names ###

CLOUDIFY_CLI = 'cloudify-cli'
CLOUDIFY_MANAGER = 'cloudify-manager'
CLOUDIFY_UI = 'cloudify-ui'
CLOUDIFY_VSPHERE_PLUGIN = 'cloudify-vsphere-plugin'

### committers ###

DAN_KILMAN = 'Dan Kilman'
EREZ_CARMEL = 'erezcarmel'
MICAEL_SVERDLIK = 'Michael Sverdlik'
NIR0S = 'nir0s'
KOSTYA = 'Kostya'

### branches and jira keys ###

CFY_1838_KEY = 'CFY-1838'
CFY_1838_SPLIT_CONTAINERS = 'CFY-1838-split-containers'

CFY_2938_KEY = 'CFY-2938'
CFY_2938_KIBANA_POC = 'CFY-2938-kibana-poc'

CFY_2709_KEY = 'CFY-2709'
CFY_2709_FIX_WINDOWS = 'CFY-2709_fix_windows_cli_requirements_file'

CFY_NO_DASH_KEY = 'CFY-2756'
CFY_NO_DASH = 'CFY2756'

CFY_GIVEAWAY_KEY = None
CFY_GIVEAWAY = 'CFY-GIVEAWAY'

SURPLUS_REMOVE_TRAVIS_SUDO = 'remove-travis-sudo'

class TestGitHubObjects(TestCase):

    def setUp(self):
        super(TestGitHubObjects, self).setUp()

        self.repo_cloudify_manager = Repo(CLOUDIFY_MANAGER)
        self.cfy_1838_issue = Issue(CFY_1838_KEY,
                                    Issue.STATUS_RESOLVED)
        self.cfy_1838_branch = Branch(CFY_1838_SPLIT_CONTAINERS,
                                      self.repo_cloudify_manager,
                                      jira_issue=self.cfy_1838_issue,
                                      last_committer=MICAEL_SVERDLIK)

        self.repo_cloudify_ui = Repo(CLOUDIFY_UI)
        self.cfy_2938_issue = Issue(CFY_2938_KEY,
                                    Issue.STATUS_CLOSED)
        self.cfy_2938_branch = Branch(CFY_2938_KIBANA_POC,
                                      self.repo_cloudify_ui,
                                      jira_issue=self.cfy_2938_issue,
                                      last_committer=EREZ_CARMEL)

        self.repo_cloudify_cli = Repo(CLOUDIFY_CLI)
        self.cfy_2709_issue = Issue(CFY_2709_KEY,
                                    Issue.STATUS_RESOLVED)
        self.cfy_2709_branch = Branch(CFY_2709_FIX_WINDOWS,
                                      self.repo_cloudify_cli,
                                      jira_issue=self.cfy_2709_issue,
                                      last_committer=MICAEL_SVERDLIK)

        self.cfy_no_dash_repo = Repo(CLOUDIFY_VSPHERE_PLUGIN)
        self.cfy_no_dash_issue = Issue(CFY_NO_DASH_KEY,
                                       Issue.STATUS_RESOLVED)

        self.cfy_no_dash_branch = Branch(CFY_NO_DASH,
                                         self.cfy_no_dash_repo,
                                         jira_issue=self.cfy_no_dash_issue,
                                         last_committer=KOSTYA
                                         )

        self.cfy_giveaway_issue = None
        self.cfy_giveaway_cloudify_manager \
            = Branch(CFY_GIVEAWAY,
                     self.repo_cloudify_manager,
                     last_committer=NIR0S
                     )

        self.surplus_branch_remove_travis_sudo \
            = Branch(SURPLUS_REMOVE_TRAVIS_SUDO,
                     self.repo_cloudify_manager,
                     last_committer=DAN_KILMAN
                     )


class TestRepo(TestGitHubObjects):

    repo = Repo(CLOUDIFY_MANAGER)

    def test_init_number_of_args(self):
        self.assertRaises(TypeError, Repo, CLOUDIFY_MANAGER, CLOUDIFY_UI)
        self.assertRaises(TypeError, Repo)

    def test_eq_equal(self):

        other_repo = Repo(CLOUDIFY_MANAGER)
        self.assertEqual(self.repo_cloudify_manager, other_repo)

    def test_ne_different(self):

        self.assertNotEqual(self.repo_cloudify_manager,
                            self.repo_cloudify_ui)

        self.assertNotEqual(self.repo_cloudify_manager,
                            None)

    def test_ne_extra_attribute(self):

        other_repo = Repo(CLOUDIFY_MANAGER)
        other_repo.extra_attribute = None
        self.assertNotEqual(self.repo_cloudify_manager, other_repo)

    def test_lt_less_than(self):

        equal_repo = Repo(CLOUDIFY_MANAGER)

        self.assertFalse(self.repo_cloudify_manager <
                         self.repo_cloudify_cli)
        self.assertFalse(self.repo_cloudify_manager <
                         equal_repo)
        self.assertTrue(self.repo_cloudify_manager <
                        self.repo_cloudify_ui)

    def test_lt_sorted(self):

        repos = [self.repo_cloudify_manager,
                 self.repo_cloudify_ui,
                 self.repo_cloudify_cli
                ]

        sorted_repos = [self.repo_cloudify_cli,
                        self.repo_cloudify_manager,
                        self.repo_cloudify_ui
                        ]

        self.assertNotEqual(repos, sorted_repos)
        self.assertEqual(sorted(repos), sorted_repos)

    def test_str(self):

        self.assertEqual(str(self.repo_cloudify_manager),
                         'Repository: {}'.format(CLOUDIFY_MANAGER)
                         )

        self.assertNotEqual(str(self.repo_cloudify_manager),
                            str(self.repo_cloudify_ui))

    def test_repr(self):

        self.assertEqual(repr(self.repo_cloudify_manager),
                         'Repo(name={})'.format(CLOUDIFY_MANAGER)
                         )

        self.assertNotEqual(str(self.repo_cloudify_manager),
                            str(self.repo_cloudify_ui))


class TestBranch(TestGitHubObjects):

    def test_init_number_of_args(self):
        self.assertRaises(TypeError, Branch,
                          CFY_1838_SPLIT_CONTAINERS,
                          self.repo_cloudify_manager,
                          another_arg='another arg',
                          jira_issue=self.cfy_1838_issue,
                          last_committer=MICAEL_SVERDLIK
                          )
        self.assertRaises(TypeError, Branch,
                          CFY_1838_SPLIT_CONTAINERS,
                          jira_issue=self.cfy_1838_issue,
                          last_committer=MICAEL_SVERDLIK
                          )

    def test_eq_equal(self):

        other_branch = Branch(CFY_1838_SPLIT_CONTAINERS,
                              self.repo_cloudify_manager,
                              jira_issue=self.cfy_1838_issue,
                              last_committer=MICAEL_SVERDLIK)
        self.assertEqual(self.cfy_1838_branch, other_branch)

    def test_ne_different(self):

        self.assertNotEqual(self.cfy_1838_branch,
                            self.cfy_2709_branch)

        self.assertNotEqual(self.cfy_1838_branch,
                            None)

        self.assertNotEqual(self.cfy_1838_branch,
                            self.surplus_branch_remove_travis_sudo)


    def test_ne_extra_attribute(self):

        other_branch = Branch(CFY_1838_SPLIT_CONTAINERS,
                                   self.repo_cloudify_manager,
                                   jira_issue=self.cfy_1838_issue,
                                   last_committer=MICAEL_SVERDLIK)

        other_branch.extra_attribute = None
        self.assertNotEqual(self.cfy_1838_branch,
                            other_branch)

    def test_lt_less_than(self):

        equal_branch = Branch(CFY_2709_FIX_WINDOWS,
                              self.repo_cloudify_cli,
                              jira_issue=self.cfy_2709_issue,
                              last_committer=MICAEL_SVERDLIK)

        self.assertFalse(self.cfy_2709_branch <
                         self.cfy_1838_branch)
        self.assertFalse(self.cfy_2709_branch <
                         equal_branch)
        self.assertTrue(self.cfy_2709_branch <
                        self.cfy_2938_branch)

    def test_lt_sorted(self):

        branches = [self.cfy_2709_branch,
                    self.cfy_2938_branch,
                    self.surplus_branch_remove_travis_sudo,
                    self.cfy_1838_branch
                    ]

        sorted_branches = [self.cfy_1838_branch,
                           self.cfy_2709_branch,
                           self.cfy_2938_branch,
                           self.surplus_branch_remove_travis_sudo
                           ]

        self.assertNotEqual(branches, sorted_branches)
        self.assertEqual(sorted(branches), sorted_branches)

    def test_str(self):

        self.assertEqual(str(self.cfy_1838_branch),
                         'Branch name: {}\n{}Last committer: {}\n'
                         .format(self.cfy_1838_branch.name,
                                 'JIRA status: ' +
                                 self.cfy_1838_branch.jira_issue.status +
                                 '\n',
                                 self.cfy_1838_branch.last_committer)
                         )

        self.assertEqual(str(self.surplus_branch_remove_travis_sudo),
                         'Branch name: {}\n{}Last committer: {}\n'
                         .format(self.surplus_branch_remove_travis_sudo.name,
                                 '',
                                 self.surplus_branch_remove_travis_sudo.
                                 last_committer)
                         )

        self.assertNotEqual(str(self.repo_cloudify_manager),
                            str(self.repo_cloudify_ui))

        self.assertNotEqual(str(self.repo_cloudify_manager),
                            str(self.surplus_branch_remove_travis_sudo))


class TestIssue(TestGitHubObjects):

    def test_init_number_of_args(self):
        self.assertRaises(TypeError, Issue,
                          CFY_1838_KEY,
                          Issue.STATUS_RESOLVED,
                          another_arg='another arg'
                          )
        self.assertRaises(TypeError, Branch,
                          CFY_1838_KEY
                          )

    def test_eq_equal(self):

        other_issue = Issue(self.cfy_1838_issue.key,
                            self.cfy_1838_issue.status)

        self.assertEqual(self.cfy_1838_issue, other_issue)

    def test_ne_different(self):

        self.assertNotEqual(self.cfy_1838_issue,
                            None)

        self.assertNotEqual(self.cfy_1838_issue,
                            self.cfy_2709_issue)

        self.assertNotEqual(self.cfy_1838_issue,
                            self.cfy_2938_issue)

    def test_str(self):

        self.assertEqual(str(self.cfy_1838_issue),
                         'JIRA status: {}\n'
                         .format(self.cfy_1838_issue.status)
                         )

        self.assertNotEqual(self.cfy_1838_issue,
                            self.cfy_2709_issue
                            )

        self.assertNotEqual(self.cfy_1838_issue,
                            ''
                            )

        self.assertNotEqual(self.cfy_1838_issue,
                            None
                            )

    def test_extract_issue_key(self):

            self.assertEqual(Issue.extract_issue_key(self.cfy_1838_branch),
                             CFY_1838_KEY)

            self.assertNotEqual(Issue.extract_issue_key(self.cfy_1838_branch),
                                None)

            self.assertEqual(Issue.extract_issue_key(self.cfy_giveaway_cloudify_manager),
                             CFY_GIVEAWAY_KEY)

            self.assertNotEqual(Issue.extract_issue_key(self.cfy_giveaway_cloudify_manager),
                                'CFY-GIVEAWAY')

            self.assertEqual(Issue.extract_issue_key(self.cfy_no_dash_branch),
                             CFY_NO_DASH_KEY)

            self.assertNotEqual(Issue.extract_issue_key(self.cfy_no_dash_branch),
                                'CFY2756')