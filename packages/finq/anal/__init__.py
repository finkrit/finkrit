# finkrit/packages/finq/analytics/__init__.py
from packages.finq.anal.returns import calculate_returns
from packages.finq.anal.risk import beta

__all__ = ["calculate_returns", "beta"]