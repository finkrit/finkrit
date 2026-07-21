# finkrit/packages/finkritq/tests/anal/risk/test_concentration.py
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk import (
    concentration_ratio,
    effective_holdings,
    exposure_by_group,
    herfindahl_index,
    max_weight,
    portfolio_concentration,
    portfolio_exposure,
)


class TestHerfindahl:

    def test_equal_weights_give_one_over_n(self):
        assert np.isclose(herfindahl_index([0.25, 0.25, 0.25, 0.25]), 0.25)

    def test_single_name_is_one(self):
        assert np.isclose(herfindahl_index([1.0]), 1.0)

    def test_matches_sum_of_squares(self):
        assert np.isclose(herfindahl_index([0.6, 0.4]), 0.52)


class TestEffectiveHoldings:

    def test_is_inverse_of_hhi(self):
        assert np.isclose(effective_holdings([0.25, 0.25, 0.25, 0.25]), 4.0)

    def test_concentrated_book_has_few_effective_holdings(self):
        assert effective_holdings([0.9, 0.05, 0.05]) < 1.5


class TestConcentrationRatio:

    def test_top_n_weight(self):
        assert np.isclose(concentration_ratio([0.4, 0.3, 0.2, 0.1], 2), 0.7)

    def test_max_weight(self):
        assert np.isclose(max_weight([0.4, 0.3, 0.2, 0.1]), 0.4)


class TestExposureByGroup:

    def test_sums_weights_within_a_group(self):
        # keys can be anything hashable, use strings as stand-in assets.
        weights = {"AAPL": 0.3, "MSFT": 0.3, "JPM": 0.4}
        sector = {"AAPL": "tech", "MSFT": "tech", "JPM": "fin"}
        exposure = exposure_by_group(weights, lambda a: sector[a])
        assert np.isclose(exposure["tech"], 0.6)
        assert np.isclose(exposure["fin"], 0.4)


class TestPortfolioConcentration:
    """
    The PortfolioData entry point, which agents call. Oracle is the raw weight
    vector pulled straight off the portfolio, so the summary must agree with it.
    """

    def test_summary_matches_the_raw_weights(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        weights = list(pd.weights.values())
        summary = portfolio_concentration(pd)
        assert summary.herfindahl == pytest.approx(sum(w * w for w in weights))
        assert summary.effective_holdings == pytest.approx(1.0 / summary.herfindahl)
        assert summary.max_weight == pytest.approx(max(weights))

    def test_top_5_captures_a_two_name_book(self, two_stock_portfolio_data):
        # Only two holdings, so the top-5 weight is the whole portfolio.
        summary = portfolio_concentration(two_stock_portfolio_data)
        assert summary.top_5_weight == pytest.approx(1.0)

    def test_two_names_have_between_one_and_two_effective_holdings(
        self, two_stock_portfolio_data
    ):
        summary = portfolio_concentration(two_stock_portfolio_data)
        assert 1.0 <= summary.effective_holdings <= 2.0


class TestPortfolioExposure:
    """The PortfolioData exposure wrapper, bucketing current weights by a grouping."""

    def test_bucketing_by_ticker_recovers_each_weight(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        exposure = portfolio_exposure(pd, lambda asset: asset.ticker)
        by_ticker = {asset.ticker: weight for asset, weight in pd.weights.items()}
        assert exposure == pytest.approx(by_ticker)
        assert sum(exposure.values()) == pytest.approx(1.0)

    def test_single_bucket_captures_the_whole_portfolio(self, two_stock_portfolio_data):
        # Mapping every asset to one group sums to the full invested weight.
        exposure = portfolio_exposure(two_stock_portfolio_data, lambda asset: "equity")
        assert exposure == pytest.approx({"equity": 1.0})
