# finkrit/packages/finkritq/tests/anal/risk/test_weighting_basis.py
"""
Tests for the two portfolio return bases (WeightingBasis).

Covers three things the basis split must guarantee:
  1. defaults preserve the pre-change behavior of each metric,
  2. CONSTANT_MIX is internally consistent (var(series) == wᵀΣw), and
  3. the two bases are genuinely distinct once the portfolio has drifted.
"""
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk.variance import portfolio_variance
from finkritq.anal.risk.volatility import portfolio_volatility
from finkritq.anal.risk.valueatrisk import portfolio_value_at_risk
from finkritq.anal.risk.conditionalvalueatrisk import (
    portfolio_conditional_value_at_risk,
)
from finkritq.anal.risk.semivariance import portfolio_semivariance
from finkritq.anal.risk.downside_deviation import portfolio_downside_deviation
from finkritq.anal.risk.drawdown import (
    portfolio_drawdown,
    portfolio_maximum_drawdown,
)
from finkritq.datatype import WeightingBasis


class TestConstantMixIdentity:
    """var(constant_mix_returns) == wᵀΣw, exactly, by linearity of variance."""

    def test_annualized_variance_equals_quadratic_form(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        series = pd.constant_mix_returns()

        assert np.var(series, ddof=1) * 252 == pytest.approx(
            portfolio_variance(pd, basis=WeightingBasis.CONSTANT_MIX)
        )

    def test_constant_mix_returns_have_one_fewer_point_than_prices(
        self, two_stock_portfolio_data
    ):
        pd = two_stock_portfolio_data
        assert len(pd.constant_mix_returns()) == len(pd) - 1
        assert len(pd.realized_returns()) == len(pd) - 1


class TestDefaultsPreserveBehavior:
    """Each metric's default basis must reproduce its pre-change value."""

    def test_variance_defaults_to_constant_mix(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_variance(pd) == pytest.approx(
            portfolio_variance(pd, basis=WeightingBasis.CONSTANT_MIX)
        )

    def test_volatility_defaults_to_constant_mix(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        assert portfolio_volatility(pd) == pytest.approx(
            portfolio_volatility(pd, basis=WeightingBasis.CONSTANT_MIX)
        )

    @pytest.mark.parametrize(
        "fn",
        [
            portfolio_value_at_risk,
            portfolio_conditional_value_at_risk,
            portfolio_semivariance,
            portfolio_downside_deviation,
            portfolio_maximum_drawdown,
        ],
    )
    def test_tail_and_downside_default_to_buy_and_hold(
        self, two_stock_portfolio_data, fn
    ):
        pd = two_stock_portfolio_data
        assert fn(pd) == pytest.approx(fn(pd, basis=WeightingBasis.BUY_AND_HOLD))


class TestBasesAreDistinct:
    """A portfolio that has drifted must give different numbers per basis."""

    def test_volatility_differs_across_bases(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        cm = portfolio_volatility(pd, basis=WeightingBasis.CONSTANT_MIX)
        bh = portfolio_volatility(pd, basis=WeightingBasis.BUY_AND_HOLD)
        assert cm != pytest.approx(bh, rel=1e-9)

    def test_max_drawdown_differs_across_bases(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        cm = portfolio_maximum_drawdown(pd, basis=WeightingBasis.CONSTANT_MIX)
        bh = portfolio_maximum_drawdown(pd, basis=WeightingBasis.BUY_AND_HOLD)
        assert cm != pytest.approx(bh, rel=1e-9)

    def test_both_bases_return_finite_values(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        for basis in WeightingBasis:
            assert np.isfinite(portfolio_volatility(pd, basis=basis))
            assert np.isfinite(portfolio_value_at_risk(pd, basis=basis))
            assert np.isfinite(portfolio_maximum_drawdown(pd, basis=basis))


class TestConstantMixDrawdownReconstruction:
    """CONSTANT_MIX drawdown compounds simple returns into a wealth index."""

    def test_drawdown_is_non_positive(self, two_stock_portfolio_data):
        pd = two_stock_portfolio_data
        dd = portfolio_drawdown(pd, basis=WeightingBasis.CONSTANT_MIX)
        assert np.all(dd <= 1e-12)

    def test_uses_simple_returns_for_wealth(self, two_stock_portfolio_data):
        # The reconstruction must compound simple returns; a log-return series
        # fed to 1+r would be subtly wrong. Guard the intended convention.
        pd = two_stock_portfolio_data
        simple = pd.constant_mix_returns()
        wealth = np.cumprod(1.0 + simple)
        expected_mdd = float(
            ((wealth - np.maximum.accumulate(wealth)) / np.maximum.accumulate(wealth)).min()
        )
        assert portfolio_maximum_drawdown(
            pd, basis=WeightingBasis.CONSTANT_MIX
        ) == pytest.approx(expected_mdd)
