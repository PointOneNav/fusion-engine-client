package(default_visibility = ["//visibility:public"])

cc_binary(
    name = "raw_message_decode",
    srcs = [
        "raw_message_decode.cc",
    ],
    data = [
        "//message_decode:example_data",
    ],
    deps = [
        "//common:print_message",
        "@fusion_engine_client",
    ],
)
