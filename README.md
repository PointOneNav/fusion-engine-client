[![Total alerts](https://img.shields.io/lgtm/alerts/g/PointOneNav/fusion-engine-client.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/PointOneNav/fusion-engine-client/alerts/)

[![Language grade: C/C++](https://img.shields.io/lgtm/grade/cpp/g/PointOneNav/fusion-engine-client.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/PointOneNav/fusion-engine-client/context:cpp)

# Point One FusionEngine Client

This library provides message definitions and support functionality for interacting with Point One FusionEngine in real
time, as well as processing recorded output data.

* [Installation](#installation)
  * [Bazel](#bazel)
    * [Compiling](#compiling)
    * [Running Examples](#running-examples)
  * [CMake](#cmake)
    * [Compiling](#compiling-1)
    * [Running Examples](#running-examples-1)
* [Usage](#usage)

### Example Applications

The `examples/` directory contains example applications demonstrating how to use this library. They are:
- `message_decode` - Print the contents of messages contained in a binary file.
- `generate_data` - Generate a binary file containing a fixed set of messages.

## Installation

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
bazel-bin/message_decode/message_decode message_decode/example_data.p1bin
```

You can also use the `bazel run` command to build and run an application in one step:

```
bazel run -c opt //message_decode -- message_decode/example_data.p1bin
```

### CMake

#### Compiling

Use the following steps to compile and install this library using CMake:

```
mkdir build
cd build
cmake ..
make
make install
```

This will generate `libfusion_engine_client.so`, and install the library and header files on your system. By default,
this will also build the [example applications](#examples).

#### Running Examples

By default, the compiled example applications will be located in `build/examples/` and can be run from there:

```
./build/examples/message_decode/message_decode
```

## Usage

All FusionEngine messages are contain a `MessageHeader`, followed by the payload of the specific message. To decode an
incoming message you must:

1. Deserialize the header.
2. Validate the message by checking the CRC (optional).
3. Deserialize the payload indicated by the `message_type` field in the header.

For example:

```c++
#include <point_one/messages/core.h>

using namespace point_one::messages;

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
