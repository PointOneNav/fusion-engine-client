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
        ":measurement_headers",
    ],
)

# Core navigation solution message definitions.
cc_library(
    name = "core_headers",
    hdrs = [
        "src/point_one/fusion_engine/common/portability.h",
        "src/point_one/fusion_engine/messages/core.h",
        "src/point_one/fusion_engine/messages/defs.h",
        "src/point_one/fusion_engine/messages/solution.h",
    ],
    includes = ["src"],
)

# Raw measurement message definitions.
cc_library(
    name = "measurement_headers",
    hdrs = [
        "src/point_one/fusion_engine/messages/measurements.h",
    ],
    deps = [
        ":core_headers",
    ],
)

################################################################################
# Support Functionality
################################################################################

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
