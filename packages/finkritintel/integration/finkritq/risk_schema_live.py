# finkritintel/integration/finkritq/risk_schema_live.py
"""
Input schemas for the two multi-metric risk tools.

Both fetch their own data (the "live" path), so both take a registry. Every
field an LLM supplies is optional and every one has a defensible default, which
is the point: a model that fills in nothing but the portfolio id still gets a
correct, complete answer rather than a validation error or a guess.

``benchmark`` deliberately carries no default here. The adapter's FieldResolver
supplies the S&P 500, because which index counts as "the market" is a product
opinion and this layer does not hold those.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finkritq.asset import Asset
from finkritq.data import DataRegistry
from finkritq.datatype import RiskMetric
from finkritq.portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class PortfolioRiskLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    benchmark: Asset
    # None means every metric. See risk_live.portfolio_risk_live for why the
    # default is everything rather than a curated subset.
    metrics: tuple[RiskMetric, ...] | None = None
    start: date | None = None
    end: date | None = None
    interval: str = "1d"


@dataclass(frozen=True, slots=True)
class AssetRiskLiveInput:
    portfolio: Portfolio
    registry: DataRegistry
    benchmark: Asset
    # None means every holding in the portfolio. The model cannot enumerate
    # tickers (it holds an opaque portfolio id and nothing else), so resolving
    # them here keeps that lookup in code where the holdings already are.
    assets: tuple[Asset, ...] | None = None
    metrics: tuple[RiskMetric, ...] | None = None
    start: date | None = None
    end: date | None = None
    interval: str = "1d"
