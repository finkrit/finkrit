load("@rules_python//python:defs.bzl", "py_test")

py_test(
    name = "test_returns",
    srcs = ["test_returns.py"],
    deps = [
        "//tests:fixtures",
        "//packages/finkritq/anal:anal",
        "//packages/finkritq/datatype",
        "@pip//numpy",
        "@pip//pytest",
    ],
)
