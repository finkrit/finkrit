load("@rules_python//python:defs.bzl", "py_library")

# Shared fixtures used by all test targets
py_library(
    name = "fixtures",
    srcs = ["fixtures.py"],
    deps = [
        "//packages/finq/asset",
        "//packages/finq/datatype",
        "//packages/finq/portfolio",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)


