![Build Status](https://github.com/PointOneNav/fusion-engine-client/workflows/FusionEngine%20Client%20Build/badge.svg?branch=master)
<br/>
[![Total alerts](https://img.shields.io/lgtm/alerts/g/PointOneNav/fusion-engine-client.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/PointOneNav/fusion-engine-client/alerts/)
<br/>
[![Language grade: C/C++](https://img.shields.io/lgtm/grade/cpp/g/PointOneNav/fusion-engine-client.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/PointOneNav/fusion-engine-client/context:cpp)

# Point One FusionEngine Client

This library provides message definitions and support functionality for interacting with Point One FusionEngine in real
time, as well as processing recorded output data. Both C++ and Python are supported.

See http://docs.pointonenav.com/fusion-engine/ for the latest API documentation.

If you encounter an issue, please [submit a ticket](#reporting-issues). For questions and support, please contact
support@pointonenav.com.

* [Requirements](#requirements)
* [Directory Structure](#directory-structure)
  * [Example Applications](#example-applications)
* [Installation](#installation)
  * [CMake](#cmake)
    * [Compiling (Linux)](#compiling-linux)
    * [Compiling (Windows)](#compiling-windows)
    * [Running Examples](#running-examples-1)
  * [Bazel](#bazel)
    * [Compiling](#compiling)
    * [Running Examples](#running-examples)
  * [Python](#python)
  * [Compiling Documentation](#compiling-documentation)
* [Implementation Notes](#implementation-notes)
  * [Message Packing](#message-packing)
  * [Endianness](#endianness)
* [Usage](#usage)
  * [Body Coordinate Frame Definition](#body-coordinate-frame-definition)
* [Contributing](#contributing)
  * [Reporting Issues](#reporting-issues)
  * [Submitting Changes](#submitting-changes)

### Requirements

#### C++ Support
- C++11 or later
- CMake 3.x or Bazel 3.x
- GCC, Clang, or Microsoft Visual Studio

#### Python Support
- Python 3.4 or later

#### Documentation Build Support (Optional)
- [Doxygen](https://www.doxygen.nl/) version 1.8.18
  - Versions 1.8.19 and 1.8.20 have a known issue with `enum` documentation and do not currently work

### Directory Structure

- `<root>` - Top-level Bazel and CMake build files (C++)
  - `examples/` - C++ example applications
  - `python/` - Python source files
    - `bin/` - Application files
    - `examples/` - Python example applications
    - `fusion_engine_client` - Top Python package directory
      - `messages` - Python message definitions
  - `src/` - C++ source files
    - `point_one/`
      - `fusion_engine/`
        - `messages/` - C++ message definitions

#### Example Applications

The `examples/` directory contains example applications demonstrating how to use this library. They are:
- `message_decode` - Print the contents of messages contained in a binary file.
- `generate_data` - Generate a binary file containing a fixed set of messages.

## Installation

### CMake

#### Compiling (Linux)

Use the following steps to compile and install this library using CMake:

```
mkdir build
cd build
cmake ..
make
sudo make install
```

This will generate `libfusion_engine_client.so`, and install the library and header files on your system. By default,
this will also build the [example applications](#examples).

#### Compiling (Windows)

Use the following steps to compile and install this library using CMake and MSBuild:

```
mkdir output
cd output
cmake ..
MSBuild p1_fusion_engine_client.sln
```

> Note: For Windows, we name the build directory `output`. Windows is not case-sensitive, and `build` conflicts with the
> Bazel `BUILD` file.

#### Running Examples

By default, the compiled example applications will be located in `build/examples/` and can be run from there:

```
./build/examples/message_decode/message_decode
```

### Bazel

#### Compiling

To use this library in an existing Bazel project, add the following to your project's `WORKSPACE` file:

```python
git_repository(
    name = "fusion_engine_client",
    branch = "master",
    remote = "git@github.com:PointOneNav/fusion_engine_client.git",
)
```

Then add the following dependency to any `cc_library()` or `cc_binary()` definitions in your project:

```python
cc_library(
    name = "my_library",
    deps = [
        "@fusion_engine_client",
    ],
)
```

If desired, you can add a dependency for only part of the library. For example, to depend on only the core message
definitions and support code, set your `deps` entry to `@fusion_engine_client//:core`.

Note that there is no need to explicitly compile or link this library when using Bazel - it will be built automatically
when your application is built. If desired, however, you can build a stand-alone shared library as follows:

```
bazel build -c opt //:libfusion_engine_client.so
```

The generated file will be located at `bazel-bin/libfusion_engine_client.so`.

#### Running Examples

> Note: The `/examples` directory has been structured like a stand-alone Bazel project to illustrate how to integrate
> this library into your own project. The `bazel-bin/` directory below refers to `<root>/examples/bazel-bin/`.

To build all example applications, navigate to the `examples/` directory and run the following:

```
bazel build -c opt //:*
```

Alternatively, you can build individual applications as follows:

```
bazel build -c opt //message_decode
```

The generated applications will be located in `bazel-bin/`. For example:

```
bazel-bin/message_decode/message_decode message_decode/example_data.p1log
```

You can also use the `bazel run` command to build and run an application in one step:

```
bazel run -c opt //message_decode -- message_decode/example_data.p1log
```

### Python

The `python/` directory contains source code for reading and analyzing FusionEngine output. To use the Python library:

1. Install Python 3.4 and Pip
2. Navigate to the `python/` directory and install the requirements:
   ```
   pip install -r requirements.txt
   ```
3. Run any of the applications in `python/bin/` or the example code in `python/examples/`. For example, to plot results
   from a `*.p1log` file or recorded in an Atlas log:
   ```
   cd python/
   python3 bin/p1_display.py /path/to/log/directory
   ```

See [Point One FusionEngine Python Client](python) for more details and examples.

### Compiling Documentation

The documentation for the latest release is generated automatically and hosted at
http://docs.pointonenav.com/fusion-engine/. If you would like to build documentation locally, simply run `doxygen` from
the repository root directory. The generated output will be located in `docs/html/`. To view it, open
`docs/html/index.html` in a web browser.

## Implementation Notes

### Message Packing

The canonical definitions for the fusion engine messages are their C++ struct definitions. These definitions are given
the attributes:
 * `packed` - This attribute sets that no implicit padding should be inserted between members of the struct. For example:
   ```
   struct Foo {
     uint8_t a;
     uint64_t b;
   };
   ```
   Without the `packed` attribute, the size of `Foo` could be 12 or 16 bytes with 3 or 7 bytes of padding inserted
   between the members `a` and `b`. With `packed`, the two member variables will be back-to-back in memory.
 * `aligned(4)` - This attribute ensures that the the size of the struct will be padded at the end to be a multiple of 4
   bytes. It also makes the default alignment of the struct in memory 4 bytes as well.

In addition to these struct attributes, the struct definitions manually enforce 4 byte alignment for floating point values (i.e., `float` and `double`).

### Endianness

Generally, functions in this library assume that serialized data is little-endian.

No special detection of conversion is done to enforce this, so external handling would be needed to use this library with a big-endian system.

## Usage

All FusionEngine messages contain a `MessageHeader` followed by the payload of the specific message. To decode an
incoming message you must:

1. Deserialize the header.
2. Validate the message by checking the CRC (optional).
3. Deserialize the payload indicated by the `message_type` field in the header.

For example:

```c++
#include <point_one/fusion_engine/messages/core.h>

using namespace point_one::fusion_engine::messages;

void DeserializeMessage(const uint8_t* buffer) {
  const MessageHeader& header = *reinterpret_cast<const MessageHeader*>(buffer);
  if (header.message_type == MessageType::POSE) {
    const PoseMessage& contents =
        *reinterpret_cast<const PoseMessage*>(buffer + sizeof(MessageHeader));
    ...
  }
}
```

See the `message_decode` example for more details.

### Body Coordinate Frame Definition

<img src="docs/images/vehicle_frame_side.svg" alt="Vehicle Frame Side View" width="48%" /> <img src="docs/images/vehicle_frame_back.svg" alt="Vehicle Frame Back View" width="35%" />

The platform body axes are defined as +x forward, +y left, and +z up. A positive yaw is a left turn, positive pitch
points the nose of the vehicle down, and positive roll is a roll toward the right. Yaw is measured from east in a
counter-clockwise direction. For example, north is +90 degrees (i.e., `heading = 90.0 - yaw`).

# Contributing

We welcome code and documentation contributions from users!

## Reporting Issues

If you encounter a problem, please
[search to see if an issue exists](https://github.com/PointOneNav/fusion-engine-client/issues). If not, please
[submit a  new ticket](https://github.com/PointOneNav/fusion-engine-client/issues/new) and include the following
information:
- A description of the issue
- Steps to replicate the issue, including a minimal example if possible
- The commit hash of the [FusionEngine Client](https://github.com/PointOneNav/fusion-engine-client) repo on which you
  encountered the issue
- The type and version of operating system you are running on
- Any other information, logs, screenshots, or outputs you wish to share

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

### Make The Change

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

### Submit A Pull Request

1. If you have not already, create a fork of the
   [fusion-engine-client](https://github.com/PointOneNav/fusion-engine-client) repository on Github and add it to your
   local repository:
   ```
   git remote add my-fork git@github.com:username/fusion-engine-client.git
   ```
2. Push your new branch to your fork.
   ```
   git push my-fork my-feature
   ```
3. Go to the Github page for your fork and create a new pull request from `username:my-feature` into
   `PointOneNav:master`.
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
> git fetch origin
> git checkout my-feature
> git rebase origin/master
> git push -f my-fork my-feature
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
  - This is the reason we request [small commits with a single functional change](#make-the-change): so that each
    commit can be tested if needed to confirm that it does what it intends and doesn't cause problems.
- Conflicts are easier to resolve on larger branches since they happen at an individual commit level, and you can simply
  correct that commit so that it does what it is supposed to with the new upstream `origin/master` changes.
  - By contrast, when you have a conflict with a `git merge`, the conflicting code might include several unrelated
    changes, and it can sometimes be hard to figure out the correct resolution.

In general, rebasing is pretty simple. In order to update your code with the latest changes on `origin/master`, do the
following:

1. Fetch the latest changes.
   ```
   git fetch origin
   ```
2. Rebase your branch onto the new version of `origin/master`.
   ```
   git checkout my-feature
   git rebase origin/master
   ```
   This recreates your commits one at a time as if they were created on top of the new version of `origin/master`. If
   you hit a conflict, simply fix that commit so that it does what it was originally intended to do, and then continue
   (`git rebase --continue`).

   (Compare this with `git merge origin/master`, which you should _never_ do.)
3. Update your fork using a force push.
   ```
   git push -f my-fork my-feature
   ```

`git rebase` has a lot of other really useful features. Most notably, you can use `fixup!` commits to correct issues in
existing commits. For example, say we forgot a semicolon in a commit and that commit does not compile. We could do the
following:
```
2231360 Added a new C++ example.
ee2adc2 Fixed a serialization bug.
113b2aa Fixed missing semicolon in new example.
```
but that means that commit `2231360` can't be compiled and tested when looking for a bug. Instead, you can mark the
commit as a `fixup!`:
```
pick 2231360 Added a new C++ example.
pick ee2adc2 Fixed a serialization bug.
pick 113b2aa fixup! Added a new C++ example.
```
and then you can use an interactive rebase (`git rebase -i origin/master`) to squash them together before merging the
changes:
```
pick 2231360 Added a new C++ example.
fixup 113b2aa fixup! Added a new C++ example.
pick ee2adc2 Fixed a serialization bug.
```
The resulting commit is a combination of the original change and the semicolon fix:
```
pick aabd112 Added a new C++ example.
pick ee2adc2 Fixed a serialization bug.
```

See https://www.atlassian.com/git/tutorials/rewriting-history/git-rebase for more information about rebasing.
