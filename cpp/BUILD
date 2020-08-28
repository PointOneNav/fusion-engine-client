package(default_visibility = ["//visibility:public"])

# Default target: include all messages and supporting code.
cc_library(
    name = "cpp",
    deps = [
        ":core",
        ":messages",
    ],
)

# Message definition headers only (all message types).
cc_library(
    name = "messages",
    includes = ["."],
    deps = [
        "//cpp/point_one/messages",
    ],
)

# Core navigation solution support functionality.
cc_library(
    name = "core",
    includes = ["."],
    deps = [
        "//cpp/point_one/messages:core",
    ],
)
