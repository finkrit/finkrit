load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "asset",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq:finq",
        "//packages/finq/datatype",
    ],
    visibility = ["//visibility:public"],
)
