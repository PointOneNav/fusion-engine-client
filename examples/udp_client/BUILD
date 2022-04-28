package(default_visibility = ["//visibility:public"])

# UDP client application currently supported for Linux only.
cc_binary(
    name = "udp_client",
    deps = select({
        "@bazel_tools//src/conditions:linux_x86_64": [
            ":linux_udp_client",
        ],
        "//conditions:default": [],
    }),
)

cc_library(
    name = "linux_udp_client",
    srcs = [
        "linux_udp_client.cc",
    ],
    deps = [
        "//common:print_message",
        "@fusion_engine_client",
    ],
)
