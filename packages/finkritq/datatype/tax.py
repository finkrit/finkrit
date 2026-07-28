# finkrit/packages/finkritq/datatype/tax.py
"""
Tax domain vocabulary. The parallel of datatype/risk.py, which holds the method
enums the risk analytics are parameterized by.

Only dependency free enums belong here. The result types that lot selection
produces (RealizedLot, SaleResult) carry a TaxLot, so they stay beside the
algorithm in optimize/lotselection.py, next to HarvestReport and
TaxRebalancePlan which are shaped the same way. Pulling them up would make
datatype depend on portfolio, which depends on datatype.
"""
from enum import Enum


class LotSaleMethod(Enum):
    """Which tax lots to consume first when selling part of a position.

    The ordering is the whole tax lever. At one sale price the lots differ only
    in cost basis and holding period, so the choice decides how much gain is
    realized and whether it is taxed as short or long term.
    """

    # Value strings are stable identifiers (serialization / tool schemas); do not
    # rename without updating any persisted references.
    FIFO = "fifo"   # oldest acquired first (the IRS default when none is elected)
    LIFO = "lifo"   # newest acquired first
    HIFO = "hifo"   # highest cost-per-share first -> minimizes realized gain
