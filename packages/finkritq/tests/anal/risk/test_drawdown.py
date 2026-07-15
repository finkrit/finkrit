# finkrit/tests/risk/test_drawdown.py
from __future__ import annotations

import numpy as np
import pytest

from finkritq.anal.risk.drawdown import (
    drawdown_from_prices,
    drawdown_from_returns,
    drawdown_from_wealth,
    maximum_drawdown,
    maximum_drawdown_from_prices,
    maximum_drawdown_from_wealth,
    maximum_drawdown_from_returns,
    maximum_drawdown_from_drawdown,
    drawdown,
    portfolio_drawdown,
    portfolio_maximum_drawdown,
)
from finkritq.tests.fixtures import make_price_history


_PEAK_THEN_FALL = np.array([100.0, 110.0, 90.0, 95.0, 80.0], dtype=np.float64)
_RISING         = np.array([100.0, 101.0, 102.0, 103.0, 104.0], dtype=np.float64)


class TestDrawdown:

    def test_matches_drawdown_from_prices(self):
        h = make_price_history(_PEAK_THEN_FALL.tolist())
        np.testing.assert_allclose(drawdown(h), drawdown_from_prices(h.close))

    def test_returns_array(self):
        assert isinstance(drawdown(make_price_history(_PEAK_THEN_FALL.tolist())), np.ndarray)


class TestDrawdownFromWealth:

    @pytest.mark.parametrize("wealth", [
        np.array([1.0, 2.0, 1.5, 3.0, 2.5]),
        np.array([100.0]),
        np.array([5.0, 5.0, 5.0]),
    ])
    def test_matches_prices(self, wealth):
        np.testing.assert_allclose(drawdown_from_wealth(wealth), drawdown_from_prices(wealth))

    def test_scale_invariant(self):
        wealth = np.array([1.0, 2.0, 1.5, 3.0])
        np.testing.assert_allclose(drawdown_from_wealth(wealth), drawdown_from_wealth(wealth * 500.0))


class TestDrawdownFromPrices:

    def test_scale_invariant(self):
        prices = np.array([100.0, 120.0, 90.0, 130.0])
        np.testing.assert_allclose(drawdown_from_prices(prices), drawdown_from_prices(prices * 1000.0))

    def test_every_running_peak_is_zero(self):
        prices = np.array([5.0, 7.0, 6.0, 8.0, 8.0, 10.0])
        np.testing.assert_allclose(drawdown_from_prices(prices)[prices == np.maximum.accumulate(prices)], 0.0)

    def test_single_price(self):
        np.testing.assert_allclose(drawdown_from_prices(np.array([100.0])), np.array([0.0]))

    def test_recovery_to_new_high(self):
        np.testing.assert_allclose(drawdown_from_prices(np.array([100.0, 80.0, 120.0])), np.array([0.0, -0.2, 0.0]))

    def test_partial_recovery(self):
        np.testing.assert_allclose(drawdown_from_prices(np.array([100.0, 80.0, 90.0, 95.0])), np.array([0.0, -0.2, -0.1, -0.05]))

    def test_multiple_drawdown_cycles(self):
        prices = np.array([100.0, 120.0, 100.0, 130.0, 90.0, 150.0])
        np.testing.assert_allclose(drawdown_from_prices(prices), np.array([0.0, 0.0, -1/6, 0.0, -40/130, 0.0]))

    def test_equal_highs(self):
        np.testing.assert_allclose(drawdown_from_prices(np.array([100.0, 120.0, 120.0, 110.0, 120.0])), np.array([0.0, 0.0, 0.0, -10/120, 0.0]))

    def test_never_less_than_negative_one(self):
        assert np.all(drawdown_from_prices(np.array([100.0, 1.0, 50.0, 0.1])) >= -1.0)

    def test_manual_series(self):
        np.testing.assert_allclose(drawdown_from_prices(np.array([100.0, 120.0, 90.0, 150.0, 120.0])), np.array([0.0, 0.0, -0.25, 0.0, -0.2]))


class TestDrawdownFromReturns:

    def test_single_return(self):
        np.testing.assert_allclose(drawdown_from_returns(np.array([0.1])), np.array([0.0]))

    def test_monotonically_falling_wealth(self):
        dd = drawdown_from_returns(np.array([-0.1, -0.1, -0.1]))
        assert dd[0] == pytest.approx(0.0) and np.all(np.diff(dd) < 0.0)

    def test_all_positive_returns(self):
        np.testing.assert_allclose(drawdown_from_returns(np.array([0.05, 0.02, 0.03])), np.zeros(3))

    def test_matches_wealth(self):
        returns = np.array([0.10, -0.20, 0.30, -0.10])
        np.testing.assert_allclose(drawdown_from_returns(returns), drawdown_from_wealth(np.cumprod(1.0 + returns)))


class TestMaximumDrawdown:

    def test_equals_minimum_drawdown(self):
        prices = np.array([100.0, 150.0, 120.0, 80.0, 90.0])
        assert maximum_drawdown_from_prices(prices) == pytest.approx(drawdown_from_prices(prices).min())

    def test_from_wealth(self):
        assert maximum_drawdown_from_wealth(np.array([100.0, 110.0, 90.0])) == pytest.approx(-0.18181818)

    def test_from_returns(self):
        returns = np.array([0.1, -0.2])
        assert maximum_drawdown_from_returns(returns) == pytest.approx(maximum_drawdown_from_wealth(np.cumprod(1.0 + returns)))

    def test_from_drawdown_manual(self):
        assert maximum_drawdown_from_drawdown(np.array([0.0, -0.1, -0.25, -0.2])) == pytest.approx(-0.25)

    def test_from_drawdown_zero(self):
        assert maximum_drawdown_from_drawdown(np.zeros(5)) == pytest.approx(0.0)

    def test_from_drawdown_matches_minimum(self):
        dd = np.array([0.0, -0.05, -0.12, -0.08])
        assert maximum_drawdown_from_drawdown(dd) == pytest.approx(dd.min())

    def test_monotonic_increase(self):
        assert maximum_drawdown_from_prices(np.array([1.0, 2.0, 3.0, 4.0])) == pytest.approx(0.0)

    def test_single_price(self):
        assert maximum_drawdown_from_prices(np.array([100.0])) == pytest.approx(0.0)


class TestMaximumDrawdownFromDrawdown:

    def test_manual(self):
        assert maximum_drawdown_from_drawdown(np.array([0.0, -0.1, -0.25, -0.2])) == pytest.approx(-0.25)

    def test_zero(self):
        assert maximum_drawdown_from_drawdown(drawdown_from_prices(_RISING)) == pytest.approx(0.0)

    def test_matches_minimum(self):
        dd = np.array([0.0, -0.05, -0.12, -0.08])
        assert maximum_drawdown_from_drawdown(dd) == pytest.approx(dd.min())


class TestPortfolioDrawdown:

    def test_matches_price_drawdown(self, two_stock_portfolio_data):
        np.testing.assert_allclose(portfolio_drawdown(two_stock_portfolio_data), drawdown_from_prices(two_stock_portfolio_data.value))

    def test_matches_price_maximum_drawdown(self, two_stock_portfolio_data):
        assert portfolio_maximum_drawdown(two_stock_portfolio_data) == pytest.approx(maximum_drawdown_from_prices(two_stock_portfolio_data.value))


class TestDrawdownHistory:

    def test_matches_drawdown_from_prices(self):
        h = make_price_history(_PEAK_THEN_FALL.tolist())
        np.testing.assert_allclose(drawdown(h), drawdown_from_prices(h.close))

    def test_returns_array(self):
        assert isinstance(drawdown(make_price_history(_PEAK_THEN_FALL.tolist())), np.ndarray)

    def test_maximum_drawdown_history(self):
        h = make_price_history(_PEAK_THEN_FALL.tolist())
        assert maximum_drawdown(h) == pytest.approx(maximum_drawdown_from_prices(h.close))


    def test_matches_drawdown_from_prices(self):
        h = make_price_history(_PEAK_THEN_FALL.tolist())
        np.testing.assert_allclose(drawdown(h), drawdown_from_prices(h.close))

    def test_returns_array(self):
        assert isinstance(drawdown(make_price_history(_PEAK_THEN_FALL.tolist())), np.ndarray)

        
class TestDrawdownFromWealth:

    @pytest.mark.parametrize(
        "wealth",
        [
            np.array([1.0, 2.0, 1.5, 3.0, 2.5]),
            np.array([100.0]),
            np.array([5.0, 5.0, 5.0]),
        ],
    )
    def test_matches_prices(self, wealth):
        np.testing.assert_allclose(drawdown_from_wealth(wealth), drawdown_from_prices(wealth))

    def test_scale_invariant(self):
        wealth = np.array([1.0, 2.0, 1.5, 3.0])
        np.testing.assert_allclose(drawdown_from_wealth(wealth), drawdown_from_wealth(wealth * 500.0))


class TestDrawdownFromPrices:

    def test_scale_invariant(self):
        prices = np.array([100.0, 120.0, 90.0, 130.0])
        np.testing.assert_allclose(
            drawdown_from_prices(prices),
            drawdown_from_prices(prices * 1000.0),
        )

    def test_every_running_peak_is_zero(self):
        prices = np.array([5.0, 7.0, 6.0, 8.0, 8.0, 10.0])
        np.testing.assert_allclose(
            drawdown_from_prices(prices)[prices == np.maximum.accumulate(prices)],
            0.0,
        )

    def test_single_price(self):
        np.testing.assert_allclose(
            drawdown_from_prices(np.array([100.0])),
            np.array([0.0]),
        )

    def test_recovery_to_new_high(self):
        prices = np.array([100.0, 80.0, 120.0])
        np.testing.assert_allclose(
            drawdown_from_prices(prices),
            np.array([0.0, -0.2, 0.0]),
        )

    def test_partial_recovery(self):
        prices = np.array([100.0, 80.0, 90.0, 95.0])
        np.testing.assert_allclose(
            drawdown_from_prices(prices),
            np.array([0.0, -0.2, -0.1, -0.05]),
        )

    def test_multiple_drawdown_cycles(self):
        prices = np.array([100.0, 120.0, 100.0, 130.0, 90.0, 150.0])
        np.testing.assert_allclose(
            drawdown_from_prices(prices),
            np.array([0.0, 0.0, -1/6, 0.0, -40/130, 0.0]),
        )

    def test_equal_highs(self):
        prices = np.array([100.0, 120.0, 120.0, 110.0, 120.0])
        np.testing.assert_allclose(drawdown_from_prices(prices), np.array([0.0, 0.0, 0.0, -10/120, 0.0]))

    def test_never_less_than_negative_one(self):
        assert np.all(drawdown_from_prices(np.array([100.0, 1.0, 50.0, 0.1])) >= -1.0)

    def test_manual_series(self):
        prices = np.array([100.0, 120.0, 90.0, 150.0, 120.0])
        np.testing.assert_allclose(
            drawdown_from_prices(prices),
            np.array([0.0, 0.0, -0.25, 0.0, -0.2]),
        )


class TestDrawdownFromReturns:

    def test_single_return(self):
        np.testing.assert_allclose(
            drawdown_from_returns(np.array([0.1])),
            np.array([0.0]),
        )

    def test_monotonically_falling_wealth(self):
        dd = drawdown_from_returns(np.array([-0.1, -0.1, -0.1]))
        assert dd[0] == pytest.approx(0.0)
        assert np.all(np.diff(dd) < 0.0)

    def test_all_positive_returns(self):
        np.testing.assert_allclose(
            drawdown_from_returns(np.array([0.05, 0.02, 0.03])),
            np.zeros(3),
        )

    def test_matches_wealth(self):
        returns = np.array([0.10, -0.20, 0.30, -0.10])
        wealth = np.cumprod(1.0 + returns)
        np.testing.assert_allclose(
            drawdown_from_returns(returns),
            drawdown_from_wealth(wealth),
        )


class TestMaximumDrawdown:

    def test_equals_minimum_drawdown(self):
        prices = np.array([100.0, 150.0, 120.0, 80.0, 90.0])
        assert maximum_drawdown_from_prices(prices) == pytest.approx(
            drawdown_from_prices(prices).min()
        )

    def test_from_wealth(self):
        assert maximum_drawdown_from_wealth(
            np.array([100.0, 110.0, 90.0])
        ) == pytest.approx(-0.18181818)

    def test_from_returns(self):
        returns = np.array([0.1, -0.2])
        assert maximum_drawdown_from_returns(returns) == pytest.approx(
            maximum_drawdown_from_wealth(np.cumprod(1.0 + returns))
        )

    def test_from_drawdown_manual(self):
        assert maximum_drawdown_from_drawdown(
            np.array([0.0, -0.1, -0.25, -0.2])
        ) == pytest.approx(-0.25)

    def test_from_drawdown_zero(self):
        assert maximum_drawdown_from_drawdown(
            np.zeros(5)
        ) == pytest.approx(0.0)

    def test_from_drawdown_matches_minimum(self):
        dd = np.array([0.0, -0.05, -0.12, -0.08])
        assert maximum_drawdown_from_drawdown(dd) == pytest.approx(dd.min())

    def test_monotonic_increase(self):
        assert maximum_drawdown_from_prices(
            np.array([1.0, 2.0, 3.0, 4.0])
        ) == pytest.approx(0.0)

    def test_single_price(self):
        assert maximum_drawdown_from_prices(
            np.array([100.0])
        ) == pytest.approx(0.0)


class TestMaximumDrawdownFromDrawdown:

    def test_manual(self):
        assert maximum_drawdown_from_drawdown(np.array([0.0, -0.1, -0.25, -0.2])) == pytest.approx(-0.25)

    def test_zero(self):
        assert maximum_drawdown_from_drawdown(drawdown_from_prices(_RISING)) == pytest.approx(0.0)

    def test_matches_minimum(self):
        dd = np.array([0.0, -0.05, -0.12, -0.08])
        assert maximum_drawdown_from_drawdown(dd) == pytest.approx(dd.min())


class TestPortfolioDrawdown:

    def test_matches_price_drawdown(self, two_stock_portfolio_data):
        np.testing.assert_allclose(portfolio_drawdown(two_stock_portfolio_data), drawdown_from_prices(two_stock_portfolio_data.value))

    def test_matches_price_maximum_drawdown(self, two_stock_portfolio_data):
        assert portfolio_maximum_drawdown(two_stock_portfolio_data) == pytest.approx(maximum_drawdown_from_prices(two_stock_portfolio_data.value))


class TestDrawdownHistory:

    def test_matches_drawdown_from_prices(self):
        h = make_price_history(_PEAK_THEN_FALL.tolist())
        np.testing.assert_allclose(drawdown(h), drawdown_from_prices(h.close))

    def test_returns_array(self):
        assert isinstance(drawdown(make_price_history(_PEAK_THEN_FALL.tolist())), np.ndarray)

    def test_maximum_drawdown_history(self):
        h = make_price_history(_PEAK_THEN_FALL.tolist())
        assert maximum_drawdown(h) == pytest.approx(maximum_drawdown_from_prices(h.close))

