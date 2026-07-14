load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "anal",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq:finq",
        "//packages/finq/datatype",
        "//packages/finq/asset",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
