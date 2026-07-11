load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "portfolio",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq:finq",
        "//packages/finq/asset",
        "//packages/finq/anal:anal",
        "//packages/finq/datatype",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
