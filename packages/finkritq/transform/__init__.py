# finkrit/packages/finkritq/transform/__init__.py
"""
Foundational numeric transforms on market data series.

Transforms turn raw data into the derived series that analytics consume. They
sit below datatype and analytics in the dependency order, so both may depend on
them. Today this is the prices-to-returns transform and its method enum.
"""
from finkritq.transform.returns import ReturnCalculationMethod, periodic_returns

__all__ = [
    "ReturnCalculationMethod",
    "periodic_returns",
]
