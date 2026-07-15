load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "risk",
    imports = [".."],
    srcs = glob(["*.py"]),
    deps = [
        "//packages/finkritq:finq",
        "//packages/finkritq/anal:anal",
        "//packages/finkritq/data:data",
        "//packages/finkritq/datatype",
        "//packages/finkritq/asset",
        "@pip//numpy",
        "@pip//scipy",
    ],
    visibility = ["//visibility:public"],
)
