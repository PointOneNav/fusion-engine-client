package(default_visibility = ["//visibility:public"])

cc_binary(
    name = "message_decode",
    srcs = [
        "message_decode.cc",
    ],
    data = [
        "example_data.p1log",
    ],
    deps = [
        "//common:print_message",
        "@fusion_engine_client",
    ],
)
