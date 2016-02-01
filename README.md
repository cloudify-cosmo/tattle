# Tattle

tattle is a tool that enables you to dig a little deeper in your GitHub projects (and even their related JIRA issues).


## Installation
```
pip install tattle
```
## Setup - Setting Environment Variables

### Github API request limitations
As part of it's operation, tattle interacts with the GibHub API. For unauthenticated users, GitHub [limits the number of API requests to 60 per hour](https://developer.github.com/v3/#rate-limiting). While this limitation still enables tattle to perform small queries, it is highly recommended to provide tattle with GitHub credentials (username and password) before running it.

### Setting GitHub-related Environment Variables

To provide tattle with GitHub credentials, simply create two environment variables named `GITHUB_USER` and `GITHUB_PASS`, and set them with a GitHub username and a GitHub password accordingly.

For example, if your GitHub username is 'octocat' and your GitHub password is 'mypass' then you can create the environment variables (and setup tattle) as follows:
  
```
export GITHUB_USER="octocat"
export GITHUB_PASS="mypass"
```
## Usage

### Quick Example: Filtering Branches by Name

Assume that you are part of a team that works on a very large project.
This project is a product of years of development, and it contains dozens of repos and hundreds of branches. In these kinds of projects, even if every team member does everything in her power to follow naming convention and the like, it is almost inevitable this mishaps will occur. And that's where tattle comes at hand.

consider this simple config.yaml file:
```
query_config:
    data_type:        branch
    github_org:       cloudify-cosmo
    
filters:
  - type: name
    regular_expressions: [CFY]
```

With the help of this little file, tattle will create a .json report containing all the branches of the GitHub organization named 'cloudify-cosmo' whose name contains the string 'CFY'

We just need to feed that config file to tattle:
```
tattle --config-path=/path/to/config/file
```

### Let's Go Deeper! - The config.yaml File

Tattle's functionality relies on a config.yaml file.
Before getting into specifics, let's have a quick look at a sample config file:
```
---
query_config:
    thread_limit:     120
    data_type:        branch
    github_org:       cloudify-cosmo
    output_path:      /home/avia/tattle/output/report.json

filters:
  - type: name
    precedence: 1
    regular_expressions: [CFY]
        
  - type: issue
    precedence: 2
    jira_team_name: cloudifysource
    jira_statuses:  [Closed, Resolved]
    transform:
        base:               CFY-*\d+
        if_doesnt_contain:  '-'
        replace_from:       CFY
        replace_to:         CFY-
...
```
#### The Query Config Section
As you can see, the first part of this file is somewhat reminicent of the config file of our first example. Let's see what was added at the `query_config` section, and elaborate a little more on it's options.

`thread_limit` - sets the maximum number of threads used by tattle.
- unless this field is explicitly specified, tattle will use all available resources in order the perform as fast as it can. Before limiting the number of threads that tattle uses, keep in mind that interacting with external APIs over the web can take some time, especially when dealing with large GitHub project.

`data_type` - the GitHub data type that is equired by the user.
* currently, only the `branch` option is available. But there are plans to extand tattle so it will be also able to work on GitHub tags and repositories.

`github_org` - the name of the GitHub organization that we wish to enquire.

`output_path` - the path of tattle's product, the report.json file
* if an output path is not specified, the report file will be written in the system's tmp directory, under `tattle/report.json`.

#### The Filters Section

The `filters` part of config.yaml can consist of an unlimited number of filters. Regardless of the filter's type, every filter has two mandatory fields:

`type` - the type of the filter.
* currently, only `name_filter` and `issue_filter` types are available.

`precedence` - The relative order of the filter. Filters will be applied by their precedence, in ascending order.
* Tip: assign lower precedence to 'heavier' filters. As a rule of thumb, assign name filters to a higher precedence than issue filters.

name filters contain one additional field:

`regular_expressions` - a list of python styled regular expressions ('regexes'). If the list contains more than one item, the output will be a union of all the regexes. i.e, if the list is `[feature, release]`, the branches whose name includes 'feature' or 'build' (or both) won't be filtered by that name filter.
* if you never heard of regular expressions, don't worry about it. Filtering in the manner of the above example doesn't require even knowing what regexes are. Just think of the `regular_expressions` field as a list of words that you want in a branch name.

Issue filters are a bit more complex, but I'm sure that if you got until here you'll be just fine. Let's start will the simple stuff:

`cloudifysource` - the name of the JIRA team which contains your project's issues. Simple, ain't it?

`jira_statuses` - a list of all the JIRA status names that won't be filtered by that issue filter. If we refer to the above example, an issue filter whose `jira_statuses` is  `[Closed, Resolved]` will filter all branches whose corresponding JIRA issue is not 'Closed' or 'Resolved'.

But how do we get from a branch to a JIRA issue? We decided to address this issue by following a convention that is prevelant here at Cloudify. Cloudify's GitHub branches follow the naming convention `CFY-<feature-number>-<feature-description>`. [well, actually, *most* of our branches follow this convention. The fact that there are some minor divergences from this convention was one of the reasons to the development of tattle]. Anyway, with this convention at hand, we decided that the name of the corresponding issue of a `CFY-<feature-number>-<feature-description>` branch is `CFY-<feature-number>`.

From a broader prespective, what we did is to *transform* the branch's name into it's JIRA issue name. And that's where `transform` comes from. `transform`'s fields, although specifically formulated,  have quite self-explanitory names. Let's start with the first and most basic one:

`base` - a regular expression that is used to extract the (almost final) issue name from a GitHub item (in our case, a branch). Form the example transform above, we get the base `CFY-*\d+`. This regex transforms the branch name `revert-249-CFY-2504-fix-cfy-status-32m8` (told ya that some branches don't strictly follow our naming conventions) into the issue name `CFY-2504`.

Sometimes, providing only a base is enough. This is the case when transforming a branch name into an issue name is simple, or when there are no special edge cases. But for more complex cases, `transform` provides three additional fields: `if_doesnt_contain`, `replace_from`, and `replace_to`.

I will explain all three of them together, with the aid of an example based on real use case that we encountered.
Assume that you have two branches, `CFY-1001-feature1` and `CFY1002-feature2`. If we provide only the base `CFY-*\d+`, then `CFY-1001-feature1` branch will be transformed to `CFY-1001` issue, and `CFY1002-feature2` will be transformed to `CFY1002`.
But `CFY1002` is not a valid issue name - it is missing the `-`!
That's where those three fields come into play:
```
if_doesnt_contain:  '-'
replace_from:       CFY
replace_to:         CFY-
```
They are basiclly saying "if the base doesn't contain the string `-`, then replace the string `CFY` with the string `CFY-`". So, in our example, first `base` will turn `CFY1002-feature2` into `CFY1002`, and the three other fields will complete the transform by turning `CFY1002` into `CFY-1002`. That's it. Not so complex when you come to think of it.


## The Output

As mentioned earlier, tattle's output is in the form of a json file.
The files contains a list of tattle-styled GitHub branches, each of them includes the following fields:

`name` - the branch's name.

`repo` - the branch's repo name. The repo field itself also contains a field of the repo's GitHub organization (or owner).

`committer_email` - The email of the last conributer to the branch.

`jira_issue` - contains the JIRA issue status related to the branch, and that issue's name.


## More to Come

First of all, contributions are always welcome.
More specifically, our top priorities are to add support for GitHub tags and Github repos.
