package(default_visibility = ["//visibility:public"])

# All example applications.
filegroup(
  name = "examples",
  srcs = [
    "//generate_data",
    "//message_decode",
  ] +
  # TCP client application currently Linux only.
  select({
    "@bazel_tools//src/conditions:linux_x86_64": [
        "//tcp_client",
    ],
    "//conditions:default": [],
  }),
)
