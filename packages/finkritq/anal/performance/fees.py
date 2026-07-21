# finkrit/packages/finkritq/anal/performance/fees.py
"""
Gross-to-net return: reduce a return by the management fee, the net-of-fees figure
every performance report shows alongside the gross.

finq only does the math. A flat annual fee rate is applied as a haircut on value,
net = (1 + gross) * (1 - annual_fee_rate) ** years - 1, which treats the fee as a
fraction of value taken each year. This ignores intra-year timing and tiered
schedules, the actual fee schedule assigned to an owner lives above finq, only the
rate and the horizon come in here.
"""
from __future__ import annotations


def net_of_fees(gross_return: float, annual_fee_rate: float, years: float = 1.0) -> float:
    """
    Net-of-fees return from a gross return over ``years`` at ``annual_fee_rate``.

    The fee compounds as an annual haircut on value, so for a 1-year period
    net is approximately ``gross - fee``, and over multiple years the fee
    compounds like a negative return.
    """
    if not 0.0 <= annual_fee_rate < 1.0:
        raise ValueError("annual_fee_rate must be in [0, 1).")
    if years < 0.0:
        raise ValueError("years must be non-negative.")
    fee_factor = (1.0 - annual_fee_rate) ** years
    return (1.0 + gross_return) * fee_factor - 1.0
