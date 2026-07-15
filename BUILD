load("@rules_python//python:defs.bzl", "py_binary", "py_test")

py_binary(
    name = "main",
    srcs = ["main.py"],
    imports = ["packages"],
    deps = [
        "//packages/finkritq/asset",
        "//packages/finkritq/anal:anal",
        "//packages/finkritq/anal/risk:risk",
        "//packages/finkritq/data:data",
        "//packages/finkritq/data/providers:providers",
        "//packages/finkritq/portfolio",
        "//packages/finkritq/datatype",
    ],
)
