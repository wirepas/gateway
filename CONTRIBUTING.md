# How to contribute

We welcome your contributions, questions and issues regarding Wirepas
Mesh software.

If you are one of our licensees, our support channels are available to you,
otherwise please send your inquiries to opensource@wirepas.com.

## Testing

We are working on porting our tests to github and we will update
this section later in the future.

We appreciate if you can provide a simple
example on how to validate your change.

## Submitting changes

Before preparing your commit, be sure to install the developers tools.
The developers tools consist of a set of style configuration files and a
[pre-commit](https://pre-commit.com/) configuration file
([.pre-commit-config.yaml](https://github.com/wirepas/manifest/blob/master/.pre-commit-config.yaml)).

Files are stored in the [manifest repository](https://github.com/wirepas/manifest).
For your convenience, execute

```bash
    .ci/install-devtools.sh
```

to pull down all the necessary style and configuration files.
The script won't touch your environment, thus you will still need to
install other host and language requirements.

Python dependencies are specified in [dev-requirements.txt](https://github.com/wirepas/manifest/blob/master/dev-requirements.txt)
and installable with pip

```bash
    pip install dev-requirements.txt
```

On your pull request, we would like you to use atomic commits with a clear
log message such as:

```shell
    $ git commit

    "
    Change title

    A paragraph describing what this change introduces and what it aims
    to fix. Is should also mention any issue or pull request that it
    addresses, for example, closes issue #4.
    "
```

One liners are acceptable if the change is very minimal.

For merging strategies, pick either *squash and merge* or *rebase and merge*.
The strategy depends on the nature of the pull request. If the pull request
contains several commits that would make sense to keep separated in the
master history, please use rebase and merge. Otherwise, pick squash and merge.

## Branch naming

We would like to keep the branches under order. Please try to observe the
following rules:

-   **feature-\<name\>** : for a branch related to feature *name*

-   **fix-\<name\>** : for a branch that addresses the *name* bug

-   **update-\<name\>** : for a branch that aims to update *name*
    documentation or supporting *name* files

-   **add-\<name\>** : for a branch that aims to add configuration file
    for an integration/tool *name*

## Coding conventions

Here are a couple of ground rules:

-   We indent with spaces

-   We use Linux line endings

-   We use Black and flake8 for python code (automated checks on PR)

-   We use shellcheck for shell scripts (automated checks on PR)

-   We use clang-format to enforce coding style

-   We don't add a "/" on folder path variables

     :heavy_check_mark: TARGET_FOLDER=example/folder

     :heavy_multiplication_x: TARGET_FOLDER=example/folder/
