load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "interfaces",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq/data:data_init",
        "//packages/finq/asset",
        "//packages/finq/datatype",
    ],
    visibility = ["//visibility:public"],
)
