# Contributing To Point One FusionEngine Client

We welcome code and documentation contributions from users!

### Table Of Contents:
  * [Reporting Issues](#reporting-issues)
  * [Submitting Changes](#submitting-changes)
    * [Creating A Branch](#creating-a-branch)
    * [Making Changes](#making-changes)
    * [Submitting A Pull Request](#submitting-a-pull-request)
    * [Updating To The Latest Changes (Rebasing)](#updating-to-the-latest-changes-rebasing)

## Reporting Issues

If you encounter a problem, please
[search to see if an issue exists](https://github.com/PointOneNav/fusion-engine-client/issues). If not, please
[submit a new ticket](https://github.com/PointOneNav/fusion-engine-client/issues/new) and include the following
information:
- A description of the issue
- Steps to replicate the issue, including a minimal example if possible
- The commit hash of the [FusionEngine Client](https://github.com/PointOneNav/fusion-engine-client) repo on which you
  encountered the issue
- The type and version of operating system you are running on
- Any other information, logs, screenshots, or outputs you wish to share

If you need support with Point One FusionEngine or a Point One device (Atlas, Quectel LG69T, etc.), please contact
support@pointonenav.com.

## Submitting Changes

### Creating A Branch

1. Update your local copy of the [fusion-engine-client](https://github.com/PointOneNav/fusion-engine-client) repository
   to ensure you have the latest version of the code.
   ```
   git fetch origin
   ```
2. Create a new branch on top of `origin/master`.
   ```
   git checkout -b my-feature origin/master
   ```

> Important note: Do not use `git pull` to update an existing branch with new changes from `master`. Use `git rebase`
> instead. See [below](#updating-to-the-latest-changes-rebasing) for details.

Note that you should _never_ work directly on the `master` branch.

### Making Changes

1. Make your code changes and test them.
   - Note that any new C++ files or applications must be added to both CMake (`CMakeLists.txt`) and Bazel (`BUILD`)
     configuration files.
   - For Python development, we strongly recommend the use of a Python virtual environment. See
     [Using A Python Virtual Environment](python/README.md#using-a-python-virtual-environment).
2. Use a style checking tool to make sure your changes meet our coding style rules.
   - For C++, install [`clang-format`](https://clang.llvm.org/docs/ClangFormat.html) (e.g.,
     `sudo apt install clang-format`) and run as follows:
     ```
     clang-format -i path/to/file.cc
     ```
   - For Python, install [`autopep8`](https://pypi.org/project/autopep8/) (`pip install autopep8`) and run as follows:
     ```
     autopep8 -i path/to/file.py
     ```
3. Commit your changes as separate functional commits as described below.

**A good commit:**
- Has a message summarizing the change and what it is fixing (if applicable)
- Contains a single functional change to the code, where possible (e.g., fix a bug, add a new example)
- Can be compiled and tested without depending on later commits

Examples:
```
- Added a plot of navigation solution type over time.
- Fixed incorrect TCP socket timeout parameters.
```

**A bad commit:**
- Has a commit message that does not explain what you intended to do or why
- Changes multiple things at the same time, especially if the commit message
  only reflects one change (or none!)

Examples:
```
- Fixes
- It works now
```

Small, functional commits make changes easier to review, understand, and test if issues arise.

We encourage you to commit changes as you make them, and to use partial staging (`git add -p`) to commit relevant
changes together, or a Git GUI that supports partial staging such as [`git-cola`](https://git-cola.github.io/) or
[Git Kraken](https://www.gitkraken.com/).

### Submitting A Pull Request

1. If you have not already, create a fork of the
   [fusion-engine-client](https://github.com/PointOneNav/fusion-engine-client) repository on Github and add it to your
   local repository:
   ```
   git remote add username git@github.com:username/fusion-engine-client.git
   git fetch username
   ```
   We assume here and below that your local repository was cloned from the Point One repository
   (https://github.com/PointOneNav/fusion-engine-client) and `origin` refers to that repository. If instead you cloned
   from your Github fork, `origin` will refer to your fork, and you should add the Point One repository as a
   `git remote` and adjust the commands below accordingly.

   Note that we set the name of the remote to `username` to match how it appears in Github. This is not required.
2. Push your new branch to your fork.
   ```
   git push username my-feature
   ```
3. Go to the Github page for your fork and create a new pull request from
   `username/fusion-engine-client:my-feature` into `PointOneNav/fusion-engine-client:master`.
   - Your pull request summary must be a single sentence explaining the changes. For example:
     - Good: `Added a Linux TCP example C++ application.`
     - Bad: `Python changes`
   - The pull request description should include a detailed summary of any relevant changes. If possible, the summary
     should be organized into the following 3 sections as needed:
     ```
     # New Features
     - Added a Linux TCP example C++ application.

     # Changes
     - Made example message display code common between multiple example applications.

     # Fixes
     - Fixed position plotting support.
     ```

### Updating To The Latest Changes (Rebasing)

> TL;DR _Never_ use `git pull` or `git merge` when updating your code. Always use `git rebase`.
>
> ```
> git checkout my-feature
> git fetch origin
> git rebase origin/master
> git push -f username my-feature
> ```

In this repository, we make an effort to maintain a linear Git history at all times. This means that, instead of using
`git pull` to obtain the latest code changes, we use `git rebase`.

![Courtesy of https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase.](
https://wac-cdn.atlassian.com/dam/jcr:4e576671-1b7f-43db-afb5-cf8db8df8e4a/01%20What%20is%20git%20rebase.svg?cdnVersion=140)

Having a linear history has a few advantages:
- It makes the history simpler to follow by avoiding lots of merges back and forth between branches from multiple
  developers.
- It makes it possible to test changes quickly and easily when searching for the first place a bug was introduced by
  searching one commit at a time.
  - You can use `git bisect` to do this automatically.
  - This is the reason we request [small commits with a single functional change](#making-changes): so that each
    commit can be tested if needed to confirm that it does what it intends and doesn't cause problems.
- Conflicts are easier to resolve on larger branches since they happen at an individual commit level, and you can simply
  correct that commit so that it does what it is supposed to with the new upstream `origin/master` changes.
  - By contrast, when you have a conflict with a `git merge`, the conflicting code might include several unrelated
    changes, and it can sometimes be hard to figure out the correct resolution.

See https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase for more information about rebasing.

#### Updating Your Code With Rebase

In general, rebasing is pretty simple. When you rebase your branch, Git recreates each of your commits, one at a time,
as if you originally created them on top of the new version of `origin/master`. For each one, if your changes conflict
with the new `master`, Git stops and asks you to resolve them, then it continues with the remaining commits.

In order to update your code with the latest changes on `origin/master`, do  the following:

1. Fetch the latest changes.
   ```
   git fetch origin
   ```
2. Rebase your branch onto the new version of `origin/master`.
   ```
   git checkout my-feature
   git rebase origin/master
   ```

   You can read this rebase command as "recreate all of the commits on my branch as if they were written on top of the
   new version of `origin/master`."
   
   This recreates your commits starting with the first commit after you branched off of `master` previously.

   If you hit a conflict, simply fix the code so that it does what that commit was originally intended to do, stage the
   file (`git add`), and then continue with the rebase (`git rebase --continue`).

   (Compare this with `git merge origin/master`, which you should _never_ do.)
3. Finally, push the rebased changes to your fork on Github using a force push.
   ```
   git push -f username my-feature
   ```

#### Modifying Your Commits With Interactive Rebase

In addition to a normal `git rebase` above, git has a lot of other really useful features you can take advantage of by
performing an _interactive_ rebase (`git rebase -i`).

A standard rebase simply picks your commits up and puts them back down on a new version of the code -- it changes the
_base_ of your branch, hence the name re-_base_. An interactive  rebase, on the other hand, is all about editing the
commits within your branch to fix issues before you merge them.

> Note that `git rebase` and `git rebase -i` should really be thought of as different operations. You should not use
> `git rebase -i` when trying to update your code with the latest upstream changes.

For example, say we forgot a semicolon in a commit and that commit does not compile. We could simply commit the
semicolon later as follows:
```
2231360 Added a new C++ example.
ee2adc2 Fixed a serialization bug.
113b2aa Fixed missing semicolon in new example.
```

but that means that commit `2231360` can't be compiled and tested when you or someone else is looking for a bug in the
future.

Instead, you can mark the commit as a `fixup!` when setting its commit message like:
```
pick 2231360 Added a new C++ example.
pick ee2adc2 Fixed a serialization bug.
pick 113b2aa fixup! Added a new C++ example.
```

and then you can use an interactive rebase (`git rebase -i --autosquash origin/master`) to squash them together:
```
pick 2231360 Added a new C++ example.
fixup 113b2aa fixup! Added a new C++ example.
pick ee2adc2 Fixed a serialization bug.
```

Here, you can read the rebase command as "do an interactive rebase and modify all commits starting after commit
origin/master."

The resulting commit is a combination of the original change and the semicolon fix. That way, if someone comes along
later and tries to compile your commit, it works perfectly.
```
pick aabd112 Added a new C++ example.
pick ee2adc2 Fixed a serialization bug.
```
