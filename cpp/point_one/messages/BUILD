package(default_visibility = ["//visibility:public"])

# All message definitions (headers only).
cc_library(
    name = "messages",
    deps = [
        ":core",
    ],
)

# Core solution support.
cc_library(
    name = "core",
    hdrs = [
        "core.h",
        "solution.h",
    ],
    deps = [
        ":common",
    ],
)

# Common type definitions.
cc_library(
    name = "common",
    hdrs = [
        "defs.h",
    ],
)

# Utility functions.
cc_library(
    name = "utils",
    srcs = [
        "utils.cc",
    ],
    hdrs = [
        "utils.h",
    ],
    deps = [
        ":common",
        "//cpp/point_one/common:portability",
    ],
)
