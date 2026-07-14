load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "portfolio",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq:finq",
        "//packages/finkritq/asset",
        "//packages/finkritq/anal:anal",
        "//packages/finkritq/datatype",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
