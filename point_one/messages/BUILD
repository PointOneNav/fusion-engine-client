package(default_visibility = ["//visibility:public"])

# All message definitions.
cc_library(
    name = "messages",
    deps = [
        ":core",
    ],
)

# The main set of messages providing navigation solution support.
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

# Common definitions and support functions.
cc_library(
    name = "common",
    hdrs = [
        "defs.h",
    ],
)
