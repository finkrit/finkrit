load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "anal",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq:finq",
        "//packages/finkritq/datatype",
        "//packages/finkritq/asset",
        "@pip//numpy",
    ],
    visibility = ["//visibility:public"],
)
