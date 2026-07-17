# finagent/adapter/resolve.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from pydantic_ai import ModelRetry

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
    """

    param_name: str
    param_type: type
    resolve: Callable[[AgentDeps, Any], Any]


def _resolve_portfolio(deps: AgentDeps, portfolio_id: str) -> Portfolio:
    return deps.store.get_portfolio(portfolio_id)


def _resolve_asset(deps: AgentDeps, ticker: str) -> Asset:
    return deps.store.get_asset(ticker)


# Keyed by the finkritintel input_schema field name.
FIELD_RESOLVERS: dict[str, FieldResolver] = {
    "portfolio": FieldResolver("portfolio_id", str, _resolve_portfolio),
    "asset": FieldResolver("ticker", str, _resolve_asset),
    "benchmark": FieldResolver("benchmark_ticker", str, _resolve_asset),
    # PortfolioBetaLiveInput.benchmark_history_or_asset is typed as plain
    # `object` in finkritintel (PriceHistory pre-fetched, or Asset live).
    # An LLM can only ever supply a ticker, so this always resolves
    # through the Asset branch.
    "benchmark_history_or_asset": FieldResolver("benchmark_ticker", str, _resolve_asset),
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
