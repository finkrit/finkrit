load("@rules_python//python:defs.bzl", "py_test")

py_test(
    name = "test_returns",
    srcs = ["test_returns.py"],
    deps = [
        "//tests:fixtures",
        "//packages/finq/anal:anal",
        "//packages/finq/datatype",
        "@pip//numpy",
        "@pip//pytest",
    ],
)
