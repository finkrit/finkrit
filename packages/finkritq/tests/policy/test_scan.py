# finkrit/packages/finkritq/tests/policy/test_scan.py
"""
Book scan: run the policy checks across several portfolios and return only the
exceptions, worst-drift first. Flat prices give exact weights, one varying
portfolio gives the volatility a suitability check needs.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from finkritq.policy import Policy, RiskTolerance, scan_book
from finkritq.portfolio import Portfolio, PortfolioData
from finkritq.tests.fixtures import make_position, make_price_history, make_stock

_FLAT = np.full(5, 100.0)


def _portfolio(pid: str, quantities: dict[str, str]):
    stocks = {t: make_stock(t) for t in quantities}
    positions = [
        make_position(stocks[t], quantity=Decimal(q),
                      position_id=f"{pid}-p-{t}", lot_id=f"{pid}-l-{t}")
        for t, q in quantities.items()
    ]
    portfolio = Portfolio(id=pid, name=pid, positions=positions)
    data = PortfolioData(
        portfolio=portfolio,
        _histories={stocks[t]: make_price_history(_FLAT) for t in quantities},
    )
    return data, stocks


def _model(stocks) -> Policy:
    return Policy(target_weights={stock: 0.5 for stock in stocks.values()})


class TestScanBook:

    def test_compliant_book_has_no_exceptions(self):
        data, stocks = _portfolio("acct-1", {"AAA": "50", "BBB": "50"})
        assert scan_book([(data, _model(stocks))]) == []

    def test_flags_out_of_band_and_ranks_by_drift(self):
        big, s_big = _portfolio("big-drift", {"AAA": "80", "BBB": "20"})     # drift 0.60
        small, s_small = _portfolio("small-drift", {"AAA": "58", "BBB": "42"})  # drift 0.16
        onmodel, s_on = _portfolio("on-model", {"AAA": "50", "BBB": "50"})   # compliant
        book = [(small, _model(s_small)), (onmodel, _model(s_on)), (big, _model(s_big))]

        result = scan_book(book)
        assert [item.portfolio_id for item in result] == ["big-drift", "small-drift"]

    def test_on_model_but_unsuitable_is_flagged(self):
        # Real volatility, target set to the portfolio's own weights so it is on
        # model, but a zero-loss tolerance makes it unsuitable (too much risk).
        a, b = make_stock("AAA"), make_stock("BBB")
        rng = np.random.default_rng(5)
        close_a = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.012, 90))), 4)
        close_b = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.013, 90))), 4)
        positions = [
            make_position(a, quantity=Decimal("50"), position_id="p-a", lot_id="l-a"),
            make_position(b, quantity=Decimal("50"), position_id="p-b", lot_id="l-b"),
        ]
        data = PortfolioData(
            portfolio=Portfolio(id="risky", name="risky", positions=positions),
            _histories={a: make_price_history(close_a), b: make_price_history(close_b)},
        )
        policy = Policy(
            target_weights=dict(data.weights),
            risk_tolerance=RiskTolerance(floor_return=0.0),
        )

        result = scan_book([(data, policy)])
        assert len(result) == 1
        assert result[0].portfolio_id == "risky"
        assert result[0].status.in_compliance is True          # on model
        assert result[0].suitability.verdict.value == "too_much"
