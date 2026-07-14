load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "interfaces",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq/data:data_init",
        "//packages/finkritq/asset",
        "//packages/finkritq/datatype",
    ],
    visibility = ["//visibility:public"],
)
