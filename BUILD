load("@rules_python//python:defs.bzl", "py_binary", "py_test")

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [
        "//packages/finq/asset",
        "//packages/finq/anal:anal",
        "//packages/finq/anal/risk:risk",
        "//packages/finq/data:data",
        "//packages/finq/data/providers:providers",
        "//packages/finq/portfolio",
        "//packages/finq/datatype",
    ],
)
