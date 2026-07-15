load("@rules_python//python:defs.bzl", "py_library", "py_test")

# Shared fixtures + conftest available to all risk tests
py_library(
    name = "risk_fixtures",
    srcs = [
        "__init__.py",
        "conftest.py",
    ],
    deps = [
        "//tests:fixtures",
        "//packages/finkritq/data:data",
        "//packages/finkritq/portfolio",
        "//packages/finkritq/datatype",
        "@pip//numpy",
        "@pip//pytest",
    ],
    visibility = ["//tests/packages/finkritq/anal/risk:__pkg__"],
)

_COMMON_DEPS = [
    ":risk_fixtures",
    "//tests:fixtures",
    "//packages/finkritq/anal:anal",
    "//packages/finkritq/anal/risk:risk",
    "//packages/finkritq/data:data",
    "//packages/finkritq/datatype",
    "//packages/finkritq/portfolio",
    "@pip//numpy",
    "@pip//pytest",
    "@pip//scipy",
]

py_test(
    name = "test_beta",
    srcs = ["test_beta.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_covariance",
    srcs = ["test_covariance.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_correlation",
    srcs = ["test_correlation.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_variance",
    srcs = ["test_variance.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_volatility",
    srcs = ["test_volatility.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_drawdown",
    srcs = ["test_drawdown.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_semivariance",
    srcs = ["test_semivariance.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_downside_deviation",
    srcs = ["test_downside_deviation.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_marginalrisk",
    srcs = ["test_marginalrisk.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_componentrisk",
    srcs = ["test_componentrisk.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_valueatrisk",
    srcs = ["test_valueatrisk.py"],
    deps = _COMMON_DEPS,
)

py_test(
    name = "test_conditionalvalueatrisk",
    srcs = ["test_conditionalvalueatrisk.py"],
    deps = _COMMON_DEPS,
)
