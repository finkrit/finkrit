load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "datatype",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq:finq",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
