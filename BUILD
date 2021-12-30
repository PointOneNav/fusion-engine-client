package(default_visibility = ["//visibility:public"])

# Default target: include all messages and supporting code.
cc_library(
    name = "fusion_engine_client",
    deps = [
        ":core",
        ":messages",
        ":parsers",
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
        ":crc",
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
        ":ros_support",
    ],
)

# Core navigation solution message definitions.
cc_library(
    name = "core_headers",
    hdrs = [
        "src/point_one/fusion_engine/messages/configuration.h",
        "src/point_one/fusion_engine/messages/control.h",
        "src/point_one/fusion_engine/messages/core.h",
        "src/point_one/fusion_engine/messages/defs.h",
        "src/point_one/fusion_engine/messages/measurements.h",
        "src/point_one/fusion_engine/messages/solution.h",
    ],
    deps = [
        ":common",
    ],
)

# ROS translation message definitions.
cc_library(
    name = "ros_support",
    hdrs = [
        "src/point_one/fusion_engine/messages/ros.h",
    ],
    deps = [
        ":core_headers",
    ],
)

################################################################################
# Support Functionality
################################################################################

# Common support code.
cc_library(
    name = "common",
    srcs = [
        "src/point_one/fusion_engine/common/logging.cc",
    ],
    hdrs = [
        "src/point_one/fusion_engine/common/logging.h",
        "src/point_one/fusion_engine/common/portability.h",
    ],
    includes = ["src"],
)

# Message encode/decode support.
cc_library(
    name = "parsers",
    srcs = [
        "src/point_one/fusion_engine/parsers/fusion_engine_framer.cc",
    ],
    hdrs = [
        "src/point_one/fusion_engine/parsers/fusion_engine_framer.h",
    ],
    deps = [
        ":core_headers",
        ":crc",
    ],
)

# CRC support.
cc_library(
    name = "crc",
    srcs = [
        "src/point_one/fusion_engine/messages/crc.cc",
    ],
    hdrs = [
        "src/point_one/fusion_engine/messages/crc.h",
    ],
    deps = [
        ":core_headers",
    ],
)
