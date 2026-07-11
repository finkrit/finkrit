load("@rules_python//python:defs.bzl", "py_library")

# data_init exposes only __init__.py so that //packages/finq/data/interfaces
# can depend on it (to get data/__init__.py in its runfiles) without creating
# a circular BUILD dep: data → interfaces → data.
py_library(
    name = "data_init",
    srcs = ["__init__.py"],
    deps = ["//packages/finq:finq"],
    visibility = ["//visibility:public"],
)

py_library(
    name = "data",
    srcs = ["registry.py"],
    deps = [
        ":data_init",
        "//packages/finq/asset",
        "//packages/finq/data/interfaces",
        "//packages/finq/datatype",
        "//packages/finq/portfolio",
    ],
    visibility = ["//visibility:public"],
)
