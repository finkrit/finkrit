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