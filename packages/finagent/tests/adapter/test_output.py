# finagent/tests/adapter/test_output.py
"""
Direct unit tests for the output adapters.

These are module-private (`_`-prefixed) and already exercised end-to-end via
compile_tool, but their edge cases (empty array, bad type, length mismatch,
missing portfolio) are awkward to trigger through the full compiler path,
so they get direct coverage here.
"""
from __future__ import annotations

import numpy as np
import pytest

from finagent.adapter.output import _summarize_contribution, _summarize_drawdown
from finagent.tests.fixtures import make_portfolio


class TestSummarizeDrawdown:

    def test_summary_shape_and_values(self):
        # drawdowns are <= 0; min is the trough, last is "current"
        arr = np.array([0.0, -0.1, -0.25, -0.05])
        out = _summarize_drawdown(arr, {})
        assert out == {"max_drawdown": -0.25, "current_drawdown": -0.05, "periods": 4}

    def test_empty_array_is_zeroed_not_crashed(self):
        out = _summarize_drawdown(np.array([]), {})
        assert out == {"max_drawdown": 0.0, "current_drawdown": 0.0, "periods": 0}

    def test_accepts_plain_list(self):
        out = _summarize_drawdown([0.0, -0.2], {})
        assert out["max_drawdown"] == -0.2
        assert out["periods"] == 2

    def test_ignores_resolved(self):
        # resolved is part of the shared signature; drawdown doesn't read it
        assert _summarize_drawdown([0.0, -0.1], {"portfolio": object()})["periods"] == 2

    def test_non_numeric_result_raises_clearly(self):
        # a readable error, not a cryptic numpy failure downstream
        with pytest.raises((TypeError, ValueError)):
            _summarize_drawdown("not an array", {})

    def test_non_1d_result_raises_value_error(self):
        with pytest.raises(ValueError):
            _summarize_drawdown(np.array([[1.0, 2.0], [3.0, 4.0]]), {})


class TestSummarizeContribution:

    def test_maps_values_to_tickers_in_order(self):
        portfolio = make_portfolio()  # holdings AAA, BBB (in that order)
        out = _summarize_contribution(np.array([0.7, 0.3]), {"portfolio": portfolio})
        assert out == {"AAA": 0.7, "BBB": 0.3}

    def test_missing_portfolio_raises_key_error(self):
        with pytest.raises(KeyError):
            _summarize_contribution(np.array([0.5, 0.5]), {})

    def test_length_mismatch_raises_not_silent_truncation(self):
        portfolio = make_portfolio()  # 2 assets
        with pytest.raises(ValueError):
            _summarize_contribution(np.array([0.5]), {"portfolio": portfolio})

    def test_non_numeric_result_raises(self):
        # None coerces to a 0-d nan under numpy; the 1-D guard rejects it
        portfolio = make_portfolio()
        with pytest.raises((TypeError, ValueError)):
            _summarize_contribution(None, {"portfolio": portfolio})
