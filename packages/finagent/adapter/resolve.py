# finagent/adapter/resolve.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from pydantic_ai import ModelRetry

from finkritq.datatype import MarketIndex

from finagent.deps import AgentDeps

if TYPE_CHECKING:
    # Annotation-only (module uses `from __future__ import annotations`, so
    # these never evaluate at runtime). Store.get_portfolio/get_asset already
    # own the real typing -- this is just for readers/type-checkers.
    from finkritq.asset import Asset
    from finkritq.portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class FieldResolver:
    """
    Describes how one finkritintel input_schema field is exposed to the
    LLM (as a primitive) and resolved back into the domain object a
    ToolBinding implementation expects.

    ``default`` is an LLM-facing default for the primitive parameter, applied
    by the compiler when the schema field itself has none. A required
    parameter without a default turns a one shot question into a round trip:
    the model stops to ask the user for a value it should simply assume. The
    schema field stays required because the intel layer has no opinion for instance 
    the opinion (which benchmark is "the market") belongs to this adapter. 
    None means no default (dataclasses.MISSING cannot be stored, dataclasses reads
    it as "this field has no default"), so a resolver can never default a
    parameter to literal None. Resolved fields are ids of domain objects, a
    None id has no meaning, so nothing is lost.
    """

    param_name: str
    param_type: type
    resolve: Callable[[AgentDeps, Any], Any]
    default: Any = None


def _resolve_portfolio(deps: AgentDeps, portfolio_id: str) -> Portfolio:
    return deps.store.get_portfolio(portfolio_id)


def _resolve_asset(deps: AgentDeps, ticker: str) -> Asset:
    return deps.store.get_asset(ticker)


# The S&P 500, the same default the deterministic report composer uses
# (report/composer.py DEFAULT_BENCHMARK) and the asset the Assistant
# auto-registers in every store, so resolution of the default never misses.
DEFAULT_BENCHMARK_TICKER: str = MarketIndex.SP500.ticker

# Keyed by the finkritintel input_schema field name.
FIELD_RESOLVERS: dict[str, FieldResolver] = {
    "portfolio": FieldResolver("portfolio_id", str, _resolve_portfolio),
    "asset": FieldResolver("ticker", str, _resolve_asset),
    "benchmark": FieldResolver(
        "benchmark_ticker", str, _resolve_asset, default=DEFAULT_BENCHMARK_TICKER
    ),
    # PortfolioBetaLiveInput.benchmark_history_or_asset is typed as plain
    # `object` in finkritintel (PriceHistory pre-fetched, or Asset live).
    # An LLM can only ever supply a ticker, so this always resolves
    # through the Asset branch.
    "benchmark_history_or_asset": FieldResolver(
        "benchmark_ticker", str, _resolve_asset, default=DEFAULT_BENCHMARK_TICKER
    ),
}

# Supplied from AgentDeps directly; never part of the LLM-facing signature.
INJECTED_FIELDS: dict[str, Callable[[AgentDeps], Any]] = {
    "registry": lambda deps: deps.registry,
}


def resolve_field(resolver: FieldResolver, deps: AgentDeps, value: Any) -> Any:
    try:
        return resolver.resolve(deps, value)
    except KeyError as exc:
        # KeyError.__str__ re-quotes args[0]; surface the message as-is.
        message = exc.args[0] if exc.args else str(exc)
        raise ModelRetry(message) from exc
