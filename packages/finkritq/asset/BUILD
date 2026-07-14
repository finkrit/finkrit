load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "asset",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq:finq",
        "//packages/finkritq/datatype",
    ],
    visibility = ["//visibility:public"],
)
