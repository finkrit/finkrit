# finagent/cli.py
"""
Interactive CLI: a seeded fake portfolio and a chat loop against the agent.

No network, a deterministic fake price provider stands in for the live data
feed, so the numbers are reproducible and nothing is downloaded. The agent
itself is real and needs a model plus its API key in the environment.

    LLM_API_KEY=... python -m finagent --ai openai
    LLM_API_KEY=... python -m finagent --ai claude
    LLM_API_KEY=... python -m finagent -m anthropic:claude-opus-4-8

Provider-neutral: LLM_API_KEY holds the key (mapped onto whatever env var the
chosen provider expects), and the model is picked with --ai/-m, a provider
shortcut (claude, openai, gemini, groq, mistral) or a full provider:name
string. Falls back to FINKRIT_MODEL, then a default. Type a question about the
portfolio's risk, or 'quit' to leave.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from datetime import date, timedelta
from decimal import Decimal

import numpy as np

from finkritq.asset import Asset, Stock
from finkritq.data import DataRegistry
from finkritq.data.interfaces import HistoryProvider
from finkritq.datatype import Currency, Exchange, PriceHistory
from finkritq.portfolio import Portfolio, Position, TaxLot

from finagent.assistant import Assistant
from finagent.store import DEFAULT_PORTFOLIO_ID, InMemoryStore

_DEFAULT_MODEL = "anthropic:claude-sonnet-5"
_HOLDINGS = {"AAPL": "40", "MSFT": "30", "NVDA": "20", "JPM": "25", "XOM": "35"}

# Provider shortcuts for `-a`. Each maps to a sensible default model, override
# the exact model with -m/--model or FINKRIT_MODEL. pydantic-ai handles every
# provider behind the same interface, so switching is just the model string.
_PROVIDER_DEFAULTS = {
    "claude": "anthropic:claude-sonnet-5",
    "anthropic": "anthropic:claude-sonnet-5",
    "openai": "openai:gpt-5",
    "gpt": "openai:gpt-5",
    "gemini": "google-gla:gemini-2.5-pro",
    "groq": "groq:llama-3.3-70b-versatile",
    "mistral": "mistral:mistral-large-latest",
}

# The provider-specific env var each provider reads its key from. We accept one
# generic LLM_API_KEY and map it onto the right one, so our config stays neutral.
_PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google-gla": "GEMINI_API_KEY",
    "google-vertex": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


def _resolve_api_key(model: str) -> None:
    # Map the generic LLM_API_KEY onto the env var the chosen provider expects,
    # leaving a provider-native key already in the environment untouched.
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return
    provider = model.split(":", 1)[0] if ":" in model else "anthropic"
    key_env = _PROVIDER_KEY_ENV.get(provider)
    if key_env and not os.environ.get(key_env):
        os.environ[key_env] = api_key


class _FakeHistoryProvider(HistoryProvider):
    """
    Deterministic seeded daily closes per ticker, no network.

    The per-ticker seed is a stable hash, NOT Python's built-in hash(), which is
    salted per process and so would give different numbers every run. The series
    also honors the requested [start, end] window, so the lookback the agent
    reports is truthful rather than a fixed hidden range.
    """

    @staticmethod
    def _seed(ticker: str) -> int:
        digest = hashlib.blake2b(ticker.encode(), digest_size=8).digest()
        return int.from_bytes(digest, "big") % (2 ** 32)

    def history(self, asset: Asset, start=None, end=None, interval: str = "1d") -> PriceHistory:
        end = end or date.today()
        start = start or (end - timedelta(days=365))
        dates = np.arange(np.datetime64(start), np.datetime64(end), dtype="datetime64[D]")
        rng = np.random.default_rng(self._seed(asset.ticker))
        returns = rng.normal(0.0004, 0.012, len(dates))
        closes = 100.0 * np.exp(np.cumsum(returns))
        return PriceHistory(
            dates=dates.astype("datetime64[ns]"),
            open=closes, high=closes, low=closes, close=closes,
            volume=np.ones(len(dates), dtype=np.int64),
        )


def make_fake_portfolio(portfolio_id: str = DEFAULT_PORTFOLIO_ID) -> Portfolio:
    """A five-holding fake portfolio, one long-term lot per name at cost 100."""
    positions = []
    for ticker, quantity in _HOLDINGS.items():
        stock = Stock(ticker=ticker, currency=Currency.USD,
                      exchange=Exchange.NASDAQ, company_name=f"{ticker} Corp")
        lot = TaxLot(id=f"lot-{ticker}", quantity=Decimal(quantity),
                     cost_per_share=Decimal("100"), acquired=date(2022, 1, 3))
        positions.append(Position(id=f"pos-{ticker}", asset=stock, lots=(lot,)))
    return Portfolio(id=portfolio_id, name="Demo Portfolio", positions=positions)


def _registry() -> DataRegistry:
    registry = DataRegistry()
    registry.register_history(_FakeHistoryProvider())
    return registry


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m finagent",
        description="Chat with the portfolio agent over a seeded fake portfolio.",
    )
    parser.add_argument(
        "-a", "--ai", "-m", "--model", dest="ai", default=None,
        help="provider shortcut (claude, openai, gemini, groq, mistral) or a full "
             "provider:name string. Overrides FINKRIT_MODEL.",
    )
    args = parser.parse_args(argv)

    if args.ai:
        model = _PROVIDER_DEFAULTS.get(args.ai.lower(), args.ai)
    else:
        model = os.environ.get("FINKRIT_MODEL", _DEFAULT_MODEL)
    _resolve_api_key(model)
    assistant = Assistant(model=model, store=InMemoryStore(), registry=_registry())
    assistant.register_portfolio(make_fake_portfolio())

    print("=" * 64)
    print(f"  finagent CLI   model: {model}   (fake data, no network)")
    print("=" * 64)
    print("  Holdings: " + ", ".join(f"{q} {t}" for t, q in _HOLDINGS.items()))
    print("  Ask about the portfolio's risk. Try:")
    print("    - what is my portfolio's volatility?")
    print("    - what's my value at risk and max drawdown?")
    print("    - what's my beta to the S&P 500?")
    print("  Type 'quit' to exit.")

    while True:
        try:
            question = input("\nyou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break
        try:
            answer = assistant.ask(question)
        except Exception as exc:  # noqa: BLE001 - a CLI should not crash on one bad turn
            print(f"\nerror: {exc}")
            print("(if this is a model/auth error, set LLM_API_KEY and FINKRIT_MODEL)")
            continue
        print(f"\nagent > {answer}")


if __name__ == "__main__":
    main()
