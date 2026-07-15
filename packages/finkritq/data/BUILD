load("@rules_python//python:defs.bzl", "py_library")

# data_init exposes only __init__.py so that //packages/finkritq/data/interfaces
# can depend on it (to get data/__init__.py in its runfiles) without creating
# a circular BUILD dep: data → interfaces → data.
py_library(
    name = "data_init",
    imports = [".."],
    srcs = ["__init__.py"],
    deps = ["//packages/finkritq:finq"],
    visibility = ["//visibility:public"],
)

py_library(
    name = "data",
    imports = [".."],
    srcs = ["registry.py"],
    deps = [
        ":data_init",
        "//packages/finkritq/asset",
        "//packages/finkritq/data/interfaces",
        "//packages/finkritq/datatype",
        "//packages/finkritq/portfolio",
    ],
    visibility = ["//visibility:public"],
)
