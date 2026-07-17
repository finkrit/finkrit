# finagent/adapter/output.py
"""
Agent-facing output adapters.

finkritq's array-returning risk functions hand back raw NDArrays, which
(a) can't be serialized into a pydantic-ai tool-return message and
(b) are useless to an LLM even if they could. These adapters run at the
agent edge only -- finkritq keeps returning full arrays for non-agent
callers. Keyed by ToolContract.name.

Every adapter shares one signature, ``(result, resolved) -> Any``, so the
compiler can call them all identically (``_adapt(_result, resolved_dict)``).
``resolved`` holds the tool's already-resolved domain objects keyed by
finkritq field name (e.g. ``"portfolio"``); some adapters need it (mapping an
array position back to a ticker), some don't, the uniform signature is
deliberate, not an oversight.
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np

from finkritq.portfolio import Portfolio

OutputAdapter = Callable[[Any, dict[str, Any]], Any]


def _as_float_vector(result: Any) -> np.ndarray:
    """
    Coerce a finkritq array result into a 1-D float ndarray, failing with a
    clear message instead of a cryptic numpy error. In normal operation the
    binding always returns a valid array; this guards the "in practice" gap
    (a None/garbage result surfaces as a readable TypeError/ValueError).
    """
    try:
        arr = np.asarray(result, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"output adapter expected an array-like numeric result, got {type(result).__name__!r}"
        ) from exc
    if arr.ndim != 1:
        raise ValueError(f"output adapter expected a 1-D result, got shape {arr.shape}")
    return arr


def _summarize_drawdown(result: Any, resolved: dict[str, Any]) -> dict[str, float | int]:
    # `resolved` unused here -- part of the shared OutputAdapter signature.
    arr = _as_float_vector(result)
    if arr.size == 0:
        return {"max_drawdown": 0.0, "current_drawdown": 0.0, "periods": 0}
    return {
        "max_drawdown": float(arr.min()),      # most negative point (e.g. -0.23 = -23%)
        "current_drawdown": float(arr[-1]),    # drawdown as of the last observation
        "periods": int(arr.size),
    }


def _summarize_contribution(result: Any, resolved: dict[str, Any]) -> dict[str, float]:
    # finkritq returns a vector aligned to PortfolioData.assets, whose order
    # matches Portfolio.assets (both derive from Portfolio.positions order).
    portfolio: Portfolio | None = resolved.get("portfolio")
    if portfolio is None:
        raise KeyError("contribution adapter requires a resolved 'portfolio'")

    values = _as_float_vector(result)
    tickers = [asset.ticker for asset in portfolio.assets]
    # A length mismatch means the vector no longer lines up with the assets --
    # a real bug we want loud, not a silently-truncated dict from zip().
    if len(tickers) != values.size:
        raise ValueError(
            f"contribution vector length {values.size} does not match "
            f"{len(tickers)} portfolio assets"
        )
    return {ticker: float(v) for ticker, v in zip(tickers, values)}


OUTPUT_ADAPTERS: dict[str, OutputAdapter] = {
    "portfolio_drawdown": _summarize_drawdown,
    "asset_drawdown": _summarize_drawdown,
    "portfolio_marginal_contribution_to_risk": _summarize_contribution,
    "portfolio_component_contribution_to_risk": _summarize_contribution,
}
