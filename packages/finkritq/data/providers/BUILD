load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "providers",
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finq/data:data_init",
        "//packages/finq/data/interfaces",
        "//packages/finq/asset",
        "//packages/finq/datatype",
        "@pip//yfinance",
        "@pip//loguru",
    ],
    visibility = ["//visibility:public"],
)
