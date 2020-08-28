package(default_visibility = ["//visibility:public"])

# Default target: include all messages and supporting code.
cc_library(
    name = "fusion_engine_client",
    deps = [
        ":core",
        ":messages",
    ],
)

# Support for building a shared library if desired.
cc_binary(
    name = "libfusion_engine_client.so",
    linkshared = True,
    deps = [
        ":fusion_engine_client",
    ],
)

# Core navigation solution support functionality.
cc_library(
    name = "core",
    deps = [
        ":core_headers",
        ":utils",
    ],
)

################################################################################
# Message Definitions
################################################################################

# Message definition headers only (all message types).
cc_library(
    name = "messages",
    deps = [
        ":core_headers",
    ],
)

# Core navigation solution message definitions.
cc_library(
    name = "core_headers",
    hdrs = [
        "cpp/point_one/common/portability.h",
        "cpp/point_one/messages/core.h",
        "cpp/point_one/messages/defs.h",
        "cpp/point_one/messages/solution.h",
    ],
    includes = ["cpp"],
)

################################################################################
# Support Functionality
################################################################################

# Utility functions.
cc_library(
    name = "utils",
    srcs = [
        "cpp/point_one/messages/utils.cc",
    ],
    hdrs = [
        "cpp/point_one/messages/utils.h",
    ],
    deps = [
        ":core_headers",
    ],
)
