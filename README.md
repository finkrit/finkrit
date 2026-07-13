# finkrit



### Build
```
# Install Bazel (e.g. via Bazelisk)
brew install bazelisk

# First run — downloads rules_python + pip deps
bazel build //...
bazel run //:main
bazel test //tests:all
```

### Tests
```
# All tests
bazel test //tests/packages/...

# Specific sub-suite
bazel test //tests/packages/finq/anal/risk/...
bazel test //tests/packages/finq/portfolio/...
bazel test //tests/packages/finq/anal/returns:test_returns

# Single target
bazel test //tests/packages/finq/anal/risk:test_beta

# With output on failure
bazel test //tests/packages/... --test_output=errors
```