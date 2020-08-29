[![Total alerts](https://img.shields.io/lgtm/alerts/g/PointOneNav/fusion-engine-client.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/PointOneNav/fusion-engine-client/alerts/)

[![Language grade: C/C++](https://img.shields.io/lgtm/grade/cpp/g/PointOneNav/fusion-engine-client.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/PointOneNav/fusion-engine-client/context:cpp)

# Point One FusionEngine Client

This library provides message definitions and support functionality for interacting with Point One FusionEngine in real
time, as well as processing recorded output data.

* [Installation/Usage](#installationusage)
  * [Building Using Bazel](#building-using-bazel)
* [Usage](#usage)
* [Examples](#exmaples)
  * [Using Examples With Bazel](#using-examples-with-bazel)

### Building Using Bazel

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

You can also build a stand-alone shared library if desired:

```
bazel build -c opt //:libfusion_engine_client.so
```

The generated file will be located at `bazel-bin/libfusion_engine_client.so`.

## Examples

The `examples/` directory contains example applications demonstrating how to use this library. They are:
- `message_decode` - Print the contents of messages contained in a binary file.
- `generate_data` - Generate a binary file containing a fixed set of messages.

### Using Examples With Bazel

To build all example applications, navigate to the `examples/` directory and run the following:

```
bazel build -c opt //:*
```

The generated applications will be located in `bazel-bin/`. For example, `bazel-bin/message_decode/message_decode`.

Alternatively, you can build individual applications as follows:

```
bazel build -c opt //message_decode
```

You can also use the `bazel run` command to build and run an application in one step:

```
bazel run -c opt //message_decode -- message_decode/example_data.p1bin
```
