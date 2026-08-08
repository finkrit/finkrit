# finkritintel/tests/integration/test_risk_live.py
"""
The two multi-metric risk tools.

These pin the properties the collapse from twenty tools exists to provide, not
the numbers, which belong to finkritq. The load bearing ones: a call costs the
same whatever the portfolio holds, omitting an argument is always safe, and a
result never looks complete when it is not.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finkritq.datatype import PORTFOLIO_ONLY_METRICS, MarketIndex, RiskMetric
from finkritq.portfolio import Portfolio, Position, TaxLot

from finkritintel.integration.finkritq import (
    ASSET_RISK_LIVE_BINDING,
    PORTFOLIO_RISK_LIVE_BINDING,
)
from finkritintel.integration.finkritq.risk_live import (
    ASSET_METRICS,
    MAX_ASSETS_PER_CALL,
    SIGNIFICANT_FIGURES,
)
from .fixtures import make_portfolio, make_registry, make_stock

BENCHMARK = MarketIndex.SP500.as_asset()


def _portfolio_risk(**kwargs):
    return PORTFOLIO_RISK_LIVE_BINDING.execute(
        portfolio=kwargs.pop("portfolio", make_portfolio()),
        registry=make_registry(),
        benchmark=BENCHMARK,
        **kwargs,
    )


def _asset_risk(**kwargs):
    return ASSET_RISK_LIVE_BINDING.execute(
        portfolio=kwargs.pop("portfolio", make_portfolio()),
        registry=make_registry(),
        benchmark=BENCHMARK,
        **kwargs,
    )


def _portfolio_of(size: int) -> Portfolio:
    return Portfolio(
        id="big",
        name="Big",
        positions=[
            Position(
                id=f"pos-{i}",
                asset=make_stock(f"T{i:03d}"),
                lots=(
                    TaxLot(
                        id=f"lot-{i}",
                        quantity=Decimal("10"),
                        cost_per_share=Decimal("100"),
                        acquired=date(2024, 1, 1),
                    ),
                ),
            )
            for i in range(size)
        ],
    )


class TestOmittingEverythingIsSafe:
    """The property that makes a small local model usable: supply nothing but
    the portfolio and still get a real, complete answer."""

    def test_asset_risk_covers_every_holding_when_tickers_are_omitted(self):
        # The whole bug. The model holds an opaque portfolio id and can only
        # learn a ticker by receiving one in a result, so a per holding
        # question has to resolve holdings on this side.
        result = _asset_risk()
        assert set(result["holdings"]) == {"AAA", "BBB"}

    def test_omitting_metrics_computes_all_of_them(self):
        # Not a curated few. A model that fumbles the list gets a superset of
        # what it asked for, which is wasteful and never wrong; a curated
        # default would return metrics excluding what was asked and be narrated
        # as though it answered.
        assert set(_asset_risk()["computed"]) == {m.value for m in ASSET_METRICS}

    def test_portfolio_risk_computes_all_of_them_too(self):
        assert set(_portfolio_risk()["computed"]) == {m.value for m in RiskMetric}


class TestNarrowing:

    def test_asking_for_one_metric_returns_one(self):
        result = _asset_risk(metrics=(RiskMetric.BETA,))
        assert result["computed"] == ["beta"]
        assert all(set(row) == {"beta"} for row in result["holdings"].values())

    def test_asking_for_specific_tickers_narrows_the_rows(self):
        result = _asset_risk(assets=(make_stock("AAA"),), metrics=(RiskMetric.BETA,))
        assert set(result["holdings"]) == {"AAA"}


class TestSelfDescribingResults:
    """A result must never look complete when it is not. Without this, a model
    that fumbled the metric list narrates whatever it did get as the answer."""

    def test_a_narrow_call_names_what_it_did_not_compute(self):
        result = _asset_risk(metrics=(RiskMetric.BETA,))
        assert "semivariance" in result["available"]
        assert "beta" not in result["available"]

    def test_computed_and_available_never_overlap(self):
        result = _asset_risk(metrics=(RiskMetric.VOLATILITY, RiskMetric.BETA))
        assert not set(result["computed"]) & set(result["available"])

    def test_an_exhaustive_call_leaves_nothing_available(self):
        assert _portfolio_risk()["available"] == []


class TestScope:

    def test_contribution_metrics_are_portfolio_only(self):
        # They decompose a portfolio's risk across its holdings, and one asset
        # has nothing to decompose. The fact lives in finkritq next to the enum.
        assert not set(ASSET_METRICS) & PORTFOLIO_ONLY_METRICS
        assert PORTFOLIO_ONLY_METRICS <= set(RiskMetric)

    def test_the_raw_drawdown_series_is_not_offered_per_asset(self):
        # One value per trading day per holding is never what a reader wants,
        # and max_drawdown already carries the figure anyone asks for.
        assert RiskMetric.DRAWDOWN not in ASSET_METRICS

    def test_portfolio_drawdown_is_summarized_not_a_series(self):
        drawdown = _portfolio_risk(metrics=(RiskMetric.DRAWDOWN,))["metrics"]["drawdown"]
        assert set(drawdown) == {"max_drawdown", "current_drawdown", "periods"}

    def test_an_out_of_scope_metric_is_dropped_not_raised_on(self):
        # The result says what it computed, which tells a model more than an
        # exception would.
        result = _asset_risk(metrics=(RiskMetric.MARGINAL_CONTRIBUTION, RiskMetric.BETA))
        assert result["computed"] == ["beta"]


class TestCostDoesNotScaleWithHoldings:

    @pytest.mark.parametrize("size", [1, 12, MAX_ASSETS_PER_CALL])
    def test_one_call_covers_the_whole_portfolio(self, size: int):
        result = _asset_risk(portfolio=_portfolio_of(size), metrics=(RiskMetric.BETA,))
        assert len(result["holdings"]) == size

    def test_a_portfolio_past_the_cap_says_how_many_it_left_out(self):
        # Never a silent truncation: a cut list that looks whole reads as
        # "these are all your holdings" when it is not.
        oversized = MAX_ASSETS_PER_CALL + 7
        result = _asset_risk(portfolio=_portfolio_of(oversized), metrics=(RiskMetric.BETA,))
        assert len(result["holdings"]) == MAX_ASSETS_PER_CALL
        assert result["omitted_holdings"] == 7
        assert "7 not shown" in result["note"]

    def test_a_portfolio_inside_the_cap_carries_no_note(self):
        assert "note" not in _asset_risk(metrics=(RiskMetric.BETA,))


class TestPrecision:
    """Six significant figures, not decimal places. A volatility of 0.284114
    shown as a percentage to two decimals is 28.41%; rounding the ratio to
    three decimals first renders 28.40% while the dashboard, formatting the
    unrounded float, still says 28.41%."""

    def test_rounding_never_changes_a_two_decimal_percentage(self):
        # The property the dashboard depends on. Whatever we hand the model has
        # to render identically to the unrounded float the dashboard formats,
        # or the two surfaces disagree in the second decimal.
        from finkritintel.integration.finkritq.risk_live import _round

        for raw in (0.2841141592, 0.0286991, 1.0417355, 0.00087213, -0.31624999):
            assert f"{_round(raw):.2%}" == f"{raw:.2%}", raw

    def test_three_decimal_places_would_have_broken_that(self):
        # Why this is significant figures and not round(x, 3). Kept as an
        # executable record of the rejected option.
        raw = 0.2841141592
        assert f"{round(raw, 3):.2%}" != f"{raw:.2%}"

    def test_small_values_do_not_collapse_to_one_figure(self):
        # Fixed decimals flatten these: a 95% VaR of -0.0287 becomes -0.029.
        from finkritintel.integration.finkritq.risk_live import _round

        assert _round(0.00286991) == 0.00286991
        assert _round(0.2841141592) == 0.284114
        assert len(str(_round(0.2841141592)).split(".")[1]) == SIGNIFICANT_FIGURES

    def test_non_numeric_values_pass_through(self):
        from finkritintel.integration.finkritq.risk_live import _round

        assert _round("^GSPC") == "^GSPC"
        assert _round(None) is None


class TestPartialFailure:
    """One metric failing is not the answer failing. Same rule the dashboard's
    report composer follows."""

    def test_a_failing_metric_is_recorded_and_the_rest_still_arrive(self):
        # An asset the registry cannot price fails only its own rows.
        portfolio = make_portfolio()
        result = _asset_risk(portfolio=portfolio, assets=(make_stock("AAA"),))
        assert result["holdings"]["AAA"]
        assert isinstance(result["errors"], dict)

    def test_the_result_always_carries_the_bookkeeping_keys(self):
        for result in (_portfolio_risk(), _asset_risk()):
            assert set(result) >= {
                "portfolio_id", "computed", "available", "errors", "window", "units",
            }


class TestSelfDescribingUnitsAndWindow:
    """Bare floats leave a model to infer meaning, and a small one infers
    confidently and wrongly. Observed on a 14b reading these tools: VaR, a
    fraction, reported as "$204.77" per holding, and every beta reported as
    "over past 1 day interval" from reading the sampling frequency as the
    lookback. Both were gaps in the payload rather than model failures."""

    def test_every_computed_metric_carries_its_units(self):
        result = _asset_risk()
        assert set(result["units"]) == set(result["computed"])

    def test_narrowing_narrows_the_units_too(self):
        result = _asset_risk(metrics=(RiskMetric.BETA,))
        assert set(result["units"]) == {"beta"}

    def test_a_fraction_says_it_is_not_currency(self):
        # The exact fabrication: "$204.77" for a value that is 0.0205.
        units = _asset_risk(metrics=(RiskMetric.VALUE_AT_RISK,))["units"]
        assert "not a currency amount" in units["value_at_risk"]

    def test_the_window_is_a_real_period_not_the_sampling_rate(self):
        window = _asset_risk(metrics=(RiskMetric.BETA,))["window"]
        assert date.fromisoformat(window["end"]) > date.fromisoformat(window["start"])
        assert (date.fromisoformat(window["end"])
                - date.fromisoformat(window["start"])).days == 365

    def test_sampling_is_named_so_it_cannot_be_read_as_the_window(self):
        window = _asset_risk(metrics=(RiskMetric.BETA,))["window"]
        assert window["sampling"] == "1d"
        assert "sampled every 1d" in window["description"]
        assert "365 calendar days" in window["description"]

    def test_an_explicit_window_is_reported_back_as_given(self):
        result = _asset_risk(
            metrics=(RiskMetric.BETA,), start=date(2024, 1, 1), end=date(2024, 6, 30)
        )
        assert result["window"]["start"] == "2024-01-01"
        assert result["window"]["end"] == "2024-06-30"

    def test_every_metric_in_the_vocabulary_has_units(self):
        # A metric added without units would put the gap straight back.
        from finkritintel.integration.finkritq.risk_live import METRIC_UNITS

        assert set(METRIC_UNITS) == set(RiskMetric)


class TestSecurityNamesInThePayload:
    """A model handed a bare ticker supplies a company name from memory. One
    observed run labelled V as "Vanguard Utilities ETF", which is Visa. Sending
    the name the file gave us removes the reason to invent, which is cheaper
    and more reliable than detecting the invention afterwards."""

    def _named(self, ticker: str, company: str) -> Portfolio:
        from finkritq.asset import Stock
        from finkritq.datatype import Currency, Exchange

        stock = Stock(ticker=ticker, currency=Currency.USD,
                      exchange=Exchange.NASDAQ, company_name=company)
        return Portfolio(id="p", name="P", positions=[
            Position(id="pos", asset=stock, lots=(TaxLot(
                id="lot", quantity=Decimal("10"),
                cost_per_share=Decimal("100"), acquired=date(2024, 1, 1)),))])

    def test_a_real_name_is_sent(self):
        result = _asset_risk(portfolio=self._named("V", "VISA INC COM CL A"),
                             metrics=(RiskMetric.BETA,))
        assert result["names"] == {"V": "VISA INC COM CL A"}

    def test_a_placeholder_equal_to_the_ticker_is_not(self):
        # Echoing the ticker back as its own name says nothing and would read
        # as though we knew something we do not.
        result = _asset_risk(portfolio=self._named("V", "V"), metrics=(RiskMetric.BETA,))
        assert result["names"] == {}

    def test_names_never_replace_the_metrics(self):
        result = _asset_risk(portfolio=self._named("V", "VISA INC"),
                             metrics=(RiskMetric.BETA,))
        assert set(result["holdings"]["V"]) == {"beta"}
