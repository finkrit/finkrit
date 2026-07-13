# finkrit/tests/risk/test_downside_deviation.py
from __future__ import annotations

import numpy as np
import pytest

from packages.finq.anal.risk.downside_deviation import (
    downside_deviation_from_returns,
    downside_deviation_from_prices,
    downside_deviation,
    portfolio_downside_deviation,
)
from packages.finq.anal.risk.semivariance import semivariance_from_returns
from packages.finq.datatype import ReturnCalculationMethod
from tests.fixtures import make_price_history, RETURNS_A, PRICES


class TestDownsideDeviationFromReturns:

    def test_equals_sqrt_semivariance(self):
        assert downside_deviation_from_returns(RETURNS_A, annualized=False) == pytest.approx(np.sqrt(semivariance_from_returns(RETURNS_A, annualized=False)), abs=1e-10)

    def test_non_negative(self):
        assert downside_deviation_from_returns(RETURNS_A) >= 0.0

    def test_zero_for_all_positive_returns(self):
        assert downside_deviation_from_returns(np.array([0.01, 0.02, 0.005, 0.03], dtype=np.float64), annualized=False) == pytest.approx(0.0, abs=1e-12)

    def test_zero_for_constant_zero_returns(self):
        assert downside_deviation_from_returns(np.zeros(10), annualized=False) == pytest.approx(0.0)

    def test_target_increases_downside_deviation(self):
        assert downside_deviation_from_returns(np.array([0.01, 0.02, 0.03]), target=0.02, annualized=False) > 0.0

    def test_higher_target_increases_downside_deviation(self):
        assert downside_deviation_from_returns(RETURNS_A, target=0.05, annualized=False) >= downside_deviation_from_returns(RETURNS_A, target=0.0, annualized=False)

    def test_annualized_equals_scaled_non_annualized(self):
        assert downside_deviation_from_returns(RETURNS_A, annualized=True) == pytest.approx(downside_deviation_from_returns(RETURNS_A, annualized=False) * np.sqrt(252), rel=1e-9)

    def test_custom_periods_per_year(self):
        assert downside_deviation_from_returns(RETURNS_A, annualized=True, periods_per_year=12) == pytest.approx(downside_deviation_from_returns(RETURNS_A, annualized=False) * np.sqrt(12), rel=1e-9)


class TestDownsideDeviationFromPrices:

    def test_non_negative(self):
        assert downside_deviation_from_prices(PRICES) >= 0.0

    def test_constant_prices_zero(self):
        assert downside_deviation_from_prices(np.full(10, 100.0), annualized=False) == pytest.approx(0.0)

    def test_positive_trend_zero(self):
        assert downside_deviation_from_prices(np.array([100.0, 101.0, 102.0, 103.0, 104.0]), annualized=False) == pytest.approx(0.0)

    def test_matches_returns(self):
        from packages.finq.anal.returns import calculate_returns
        assert downside_deviation_from_prices(PRICES, annualized=False) == pytest.approx(downside_deviation_from_returns(calculate_returns(PRICES), annualized=False), rel=1e-9)

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, method):
        assert downside_deviation_from_prices(PRICES, method=method) >= 0.0

    def test_target_forwarded(self):
        assert downside_deviation_from_prices(PRICES, target=0.05, annualized=False) >= downside_deviation_from_prices(PRICES, target=0.0, annualized=False)

    def test_custom_periods_per_year(self):
        assert downside_deviation_from_prices(PRICES, annualized=True, periods_per_year=12) == pytest.approx(downside_deviation_from_prices(PRICES, annualized=False) * np.sqrt(12), rel=1e-9)


class TestDownsideDeviationHistory:

    def test_returns_float(self):
        assert isinstance(downside_deviation(make_price_history(PRICES.tolist())), float)

    def test_matches_prices(self):
        h = make_price_history(PRICES.tolist())
        assert downside_deviation(h, annualized=False) == pytest.approx(downside_deviation_from_prices(h.close, annualized=False), rel=1e-9)

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, method):
        assert downside_deviation(make_price_history(PRICES.tolist()), method=method) >= 0.0

    def test_target_forwarded(self):
        h = make_price_history(PRICES.tolist())
        assert downside_deviation(h, target=0.05, annualized=False) >= downside_deviation(h, target=0.0, annualized=False)

    def test_custom_periods_per_year(self):
        h = make_price_history(PRICES.tolist())
        assert downside_deviation(h, annualized=True, periods_per_year=12) == pytest.approx(downside_deviation(h, annualized=False) * np.sqrt(12), rel=1e-9)


class TestPortfolioDownsideDeviation:

    def test_non_negative(self, two_stock_portfolio_data):
        assert portfolio_downside_deviation(two_stock_portfolio_data) >= 0.0

    def test_equals_sqrt_portfolio_semivariance(self, two_stock_portfolio_data):
        from packages.finq.anal.risk.semivariance import portfolio_semivariance
        assert portfolio_downside_deviation(two_stock_portfolio_data) == pytest.approx(np.sqrt(portfolio_semivariance(two_stock_portfolio_data)), rel=1e-9)

    def test_matches_value_series(self, two_stock_portfolio_data):
        assert portfolio_downside_deviation(two_stock_portfolio_data, annualized=False) == pytest.approx(downside_deviation_from_prices(two_stock_portfolio_data.value, annualized=False), rel=1e-9)

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, two_stock_portfolio_data, method):
        assert portfolio_downside_deviation(two_stock_portfolio_data, method=method) >= 0.0

    def test_target_forwarded(self, two_stock_portfolio_data):
        assert portfolio_downside_deviation(two_stock_portfolio_data, target=0.05, annualized=False) >= portfolio_downside_deviation(two_stock_portfolio_data, target=0.0, annualized=False)

    def test_custom_periods_per_year(self, two_stock_portfolio_data):
        assert portfolio_downside_deviation(two_stock_portfolio_data, annualized=True, periods_per_year=12) == pytest.approx(portfolio_downside_deviation(two_stock_portfolio_data, annualized=False) * np.sqrt(12), rel=1e-9)



class TestDownsideDeviationFromReturns:

    def test_equals_sqrt_semivariance(self):
        sv = semivariance_from_returns(RETURNS_A, annualized=False)
        dd = downside_deviation_from_returns(RETURNS_A, annualized=False)
        assert dd == pytest.approx(np.sqrt(sv), abs=1e-10)

    def test_non_negative(self):
        assert downside_deviation_from_returns(RETURNS_A) >= 0.0

    def test_zero_for_all_positive_returns(self):
        positive = np.array([0.01, 0.02, 0.005, 0.03], dtype=np.float64)
        assert downside_deviation_from_returns(positive, annualized=False) == pytest.approx(0.0, abs=1e-12)

    def test_zero_for_constant_zero_returns(self):
        returns = np.zeros(10)
        assert downside_deviation_from_returns(returns, annualized=False) == pytest.approx(0.0)

    def test_target_increases_downside_deviation(self):
        returns = np.array([0.01, 0.02, 0.03])
        assert downside_deviation_from_returns(returns, target=0.02, annualized=False) > 0.0

    def test_higher_target_increases_downside_deviation(self):
        low = downside_deviation_from_returns(RETURNS_A, target=0.0, annualized=False)
        high = downside_deviation_from_returns(RETURNS_A, target=0.05, annualized=False)
        assert high >= low

    def test_annualized_equals_scaled_non_annualized(self):
        dd = downside_deviation_from_returns(RETURNS_A, annualized=False)
        annualized = downside_deviation_from_returns(RETURNS_A, annualized=True)
        assert annualized == pytest.approx(dd * np.sqrt(252), rel=1e-9)

    def test_custom_periods_per_year(self):
        dd = downside_deviation_from_returns(
            RETURNS_A,
            annualized=False,
        )
        annualized = downside_deviation_from_returns(
            RETURNS_A,
            annualized=True,
            periods_per_year=12,
        )
        assert annualized == pytest.approx(dd * np.sqrt(12), rel=1e-9)


class TestDownsideDeviationFromPrices:

    def test_non_negative(self):
        assert downside_deviation_from_prices(PRICES) >= 0.0

    def test_constant_prices_zero(self):
        prices = np.full(10, 100.0)
        assert downside_deviation_from_prices(prices, annualized=False) == pytest.approx(0.0)

    def test_positive_trend_zero(self):
        prices = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
        assert downside_deviation_from_prices(prices, annualized=False) == pytest.approx(0.0)

    def test_matches_returns(self):
        from packages.finq.anal.returns import calculate_returns

        returns = calculate_returns(PRICES)
        dd_prices = downside_deviation_from_prices(PRICES, annualized=False)
        dd_returns = downside_deviation_from_returns(returns, annualized=False)
        assert dd_prices == pytest.approx(dd_returns, rel=1e-9)

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, method):
        assert downside_deviation_from_prices(PRICES, method=method) >= 0.0

    def test_target_forwarded(self):
        low = downside_deviation_from_prices(
            PRICES,
            target=0.0,
            annualized=False,
        )
        high = downside_deviation_from_prices(
            PRICES,
            target=0.05,
            annualized=False,
        )
        assert high >= low

    def test_custom_periods_per_year(self):
        dd = downside_deviation_from_prices(
            PRICES,
            annualized=False,
        )
        annualized = downside_deviation_from_prices(
            PRICES,
            annualized=True,
            periods_per_year=12,
        )
        assert annualized == pytest.approx(dd * np.sqrt(12), rel=1e-9)


class TestDownsideDeviationHistory:

    def test_returns_float(self):
        h = make_price_history(PRICES.tolist())
        assert isinstance(downside_deviation(h), float)

    def test_matches_prices(self):
        h = make_price_history(PRICES.tolist())
        assert downside_deviation(h, annualized=False) == pytest.approx(
            downside_deviation_from_prices(h.close, annualized=False),
            rel=1e-9,
        )

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, method):
        h = make_price_history(PRICES.tolist())
        assert downside_deviation(h, method=method) >= 0.0

    def test_target_forwarded(self):
        h = make_price_history(PRICES.tolist())

        low = downside_deviation(
            h,
            target=0.0,
            annualized=False,
        )
        high = downside_deviation(
            h,
            target=0.05,
            annualized=False,
        )
        assert high >= low

    def test_custom_periods_per_year(self):
        h = make_price_history(PRICES.tolist())

        dd = downside_deviation(
            h,
            annualized=False,
        )
        annualized = downside_deviation(
            h,
            annualized=True,
            periods_per_year=12,
        )
        assert annualized == pytest.approx(dd * np.sqrt(12), rel=1e-9)


class TestPortfolioDownsideDeviation:

    def test_non_negative(self, two_stock_portfolio_data):
        assert portfolio_downside_deviation(two_stock_portfolio_data) >= 0.0

    def test_equals_sqrt_portfolio_semivariance(self, two_stock_portfolio_data):
        from packages.finq.anal.risk.semivariance import portfolio_semivariance

        sv = portfolio_semivariance(two_stock_portfolio_data)
        dd = portfolio_downside_deviation(two_stock_portfolio_data)
        assert dd == pytest.approx(np.sqrt(sv), rel=1e-9)

    def test_matches_value_series(self, two_stock_portfolio_data):
        assert portfolio_downside_deviation(
            two_stock_portfolio_data,
            annualized=False,
        ) == pytest.approx(
            downside_deviation_from_prices(
                two_stock_portfolio_data.value,
                annualized=False,
            ),
            rel=1e-9,
        )

    @pytest.mark.parametrize("method", list(ReturnCalculationMethod))
    def test_all_return_methods(self, two_stock_portfolio_data, method):
        assert portfolio_downside_deviation(
            two_stock_portfolio_data,
            method=method,
        ) >= 0.0

    def test_target_forwarded(self, two_stock_portfolio_data):
        low = portfolio_downside_deviation(
            two_stock_portfolio_data,
            target=0.0,
            annualized=False,
        )
        high = portfolio_downside_deviation(
            two_stock_portfolio_data,
            target=0.05,
            annualized=False,
        )
        assert high >= low

    def test_custom_periods_per_year(self, two_stock_portfolio_data):
        dd = portfolio_downside_deviation(
            two_stock_portfolio_data,
            annualized=False,
        )
        annualized = portfolio_downside_deviation(
            two_stock_portfolio_data,
            annualized=True,
            periods_per_year=12,
        )
        assert annualized == pytest.approx(dd * np.sqrt(12), rel=1e-9)


