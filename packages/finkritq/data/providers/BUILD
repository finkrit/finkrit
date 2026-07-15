load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "providers",
    imports = [".."],
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq/data:data_init",
        "//packages/finkritq/data/interfaces",
        "//packages/finkritq/asset",
        "//packages/finkritq/datatype",
        "@pip//yfinance",
        "@pip//loguru",
    ],
    visibility = ["//visibility:public"],
)
