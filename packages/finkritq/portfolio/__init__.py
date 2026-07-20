# finkrit/packages/finkritq/portfolio/__init__.py
"""
finkritq.portfolio -- the quant holdings model and the analysis views over it.

Deliberately lean and free of any ownership/legal/tax-org concepts. The unit is
``Portfolio`` (a set of ``Position``s, each holding its ``TaxLot``s), and the
analysis views ``PortfolioData`` / ``PortfolioSnapshot`` built from it and fed to
the measures. The RIA ownership graph (household, registration, account,
custodian, owner, TIN) lives *above* finq in the proprietary layer, which
flattens its holdings down to a ``Portfolio`` for analysis -- finq never sees an
account. ``TaxLot`` stays here because it is the atomic input to the OSS tax-lot
analytics (harvesting, gains, holding period), which need lot data but no org
context.
"""
from .portfolio import Portfolio
from .portfoliodata import PortfolioData
from .portfoliosnapshot import PortfolioSnapshot
from .position import Position
from .positionsnapshot import PositionSnapshot
from .taxlot import TaxLot

__all__ = [
    "Portfolio",
    "PortfolioData",
    "PortfolioSnapshot",
    "Position",
    "PositionSnapshot",
    "TaxLot",
]
