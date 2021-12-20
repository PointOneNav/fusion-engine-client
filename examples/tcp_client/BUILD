package(default_visibility = ["//visibility:public"])

# TCP client application currently supported for Linux only.
cc_binary(
    name = "tcp_client",
    deps = select({
        "@bazel_tools//src/conditions:linux_x86_64": [
            ":linux_tcp_client",
        ],
        "//conditions:default": [],
    }),
)

cc_library(
    name = "linux_tcp_client",
    srcs = [
        "linux_tcp_client.cc",
    ],
    deps = [
        "//common:print_message",
        "@fusion_engine_client",
    ],
)
