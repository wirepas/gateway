# How to contribute

We welcome your contributions, questions and issues regarding Wirepas Mesh software.

If you are one of our licensees, you can reach us through the official channels.

Otherwise, please reach us at opensource@wirepas.com

## Testing

We are working on porting our tests to github and we will update this section later in the future.

We appreaciate if you can provide a simple example on how to validate your change.

## Submitting changes

Before preparing your commit, be sure to install the pre-commit tool.

The pre-commit will install a handful of commit hooks to help us keep the code style in order and prevent information leakage
(look for dev-requirements.txt in the root of the repository or next to python packages).

On your pull request, we would like you to use atomic commits (one feature per commit).

Each commit should have a clear log message such as:

```shell
    $ git commit -m "A brief summary of the commit

    > A paragraph describing what changed and its impact."
```

One liners are accepatable if the change is very minimal.

## Branch naming

We would like to keep the branches under order. Please try to observe the following rules

-   feature-<name> : for a branch related to feature _name_
-   fix-<name> : for a branch that addresses the _name_ bug
-   update-<name> : for a branch that aims to update _name_ documentation or supporting _name_ files

## Coding conventions

Start reading our code and you'll get the hang of it. We optimize for readability:

-   We indent with spaces

-   We use Linux line endings

-   We use Black and flake8 for python code (automated checks on PR)

-   We use shellcheck and bashate for shell scripts (automated checks on PR)

-   We use [Allman's style for c code](https://en.wikipedia.org/wiki/Indentation_style#Allman_style)

-   We don't add a "/" on folder path variables 

     :heavy_check_mark: TARGET_FOLDER=example/folder 
     
     :heavy_multiplication_x: TARGET_FOLDER=example/folder/
