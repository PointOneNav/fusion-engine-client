package(default_visibility = ["//visibility:public"])

# Default target: include all messages and supporting code.
cc_library(
    name = "fusion_engine_client",
    deps = [
        ":core",
        ":messages",
        ":parsers",
        ":rtcm",
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
        "src/point_one/fusion_engine/messages/device.h",
        "src/point_one/fusion_engine/messages/fault_control.h",
        "src/point_one/fusion_engine/messages/gnss_corrections.h",
        "src/point_one/fusion_engine/messages/measurements.h",
        "src/point_one/fusion_engine/messages/signal_defs.h",
        "src/point_one/fusion_engine/messages/solution.h",
    ],
    deps = [
        ":common",
        ":data_version",
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
        "src/point_one/fusion_engine/common/version.h",
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

# Data versioning support.
cc_library(
    name = "data_version",
    srcs = [
        "src/point_one/fusion_engine/messages/data_version.cc",
    ],
    hdrs = [
        "src/point_one/fusion_engine/messages/data_version.h",
    ],
    includes = ["src"],
    deps = [
        ":common",
    ],
)

# Message encode/decode support.
cc_library(
    name = "rtcm",
    srcs = [
        "src/point_one/rtcm/rtcm_framer.cc",
    ],
    hdrs = [
        "src/point_one/rtcm/rtcm_framer.h",
    ],
    deps = [
        ":common",
    ],
)
