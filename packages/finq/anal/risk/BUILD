load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "risk",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq:finq",
        "//packages/finq/anal:anal",
        "//packages/finq/datatype",
        "//packages/finq/asset",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
