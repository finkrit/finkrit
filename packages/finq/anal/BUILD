load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "analytics",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq:finq",
        "//packages/finq/datatype",
        "//packages/finq/asset",
        "//packages/finq/data",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
