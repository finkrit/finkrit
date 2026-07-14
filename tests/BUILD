load("@rules_python//python:defs.bzl", "py_library")

# Shared fixtures used by all test targets
py_library(
    name = "fixtures",
    srcs = ["fixtures.py"],
    deps = [
        "//packages/finkritq/asset",
        "//packages/finkritq/datatype",
        "//packages/finkritq/portfolio",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)


