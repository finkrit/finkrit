# finagent/cli.py
"""
Interactive CLI: a seeded fake portfolio and a chat loop against the agent.

No network, a deterministic fake price provider stands in for the live data
feed, so the numbers are reproducible and nothing is downloaded. The agent
itself is real and needs a model plus its API key in the environment.

    LLM_API_KEY=... python -m finagent --ai openai
    LLM_API_KEY=... python -m finagent --ai claude -ag 1
    LLM_API_KEY=... python -m finagent --ai openai -ag 0

--ai picks the model, a provider shortcut (claude, openai, gemini, groq,
mistral) or a full provider:name string, keyed by a generic LLM_API_KEY mapped
onto whatever env var the provider expects. -ag picks the agent: 0 the
all-encompassing router, 1 risk, 2 optimization, 3 performance. Left off, a menu
asks. Type a question, or 'quit' to leave.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import os
import sys
import threading
import time
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from pydantic_ai.messages import FunctionToolCallEvent

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
    # leaving a provider native key already in the environment untouched.
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return
    provider = model.split(":", 1)[0] if ":" in model else "anthropic"
    key_env = _PROVIDER_KEY_ENV.get(provider)
    if key_env and not os.environ.get(key_env):
        os.environ[key_env] = api_key


# Agent menu. key -> (mode, label, description). mode None is the orchestrator,
# the other modes name a specialist for Assistant.ask.
_AGENT_CHOICES: dict[str, tuple[str | None, str, str]] = {
    "0": (None, "Router (all)", "routes and combines across specialists, costs extra LLM calls"),
    "1": ("risk", "Risk", "volatility, VaR, drawdown, beta, concentration"),
    "2": ("optimization", "Optimization", "minimum-variance / maximum-Sharpe allocations"),
    "3": ("performance", "Performance", "returns, Sharpe / Sortino / Calmar"),
}
_AGENT_NAMES = {
    "all": "0", "router": "0", "risk": "1",
    "optimization": "2", "optimize": "2", "opt": "2", "performance": "3", "perf": "3",
}


class _Spinner:
    """
    A rotating spinner on its own line while the agent thinks. Runs on a daemon
    thread so it animates during the blocking agent call, and shares a lock with
    ``line`` so a step printed mid-spin does not collide with a spinner frame.
    """

    _FRAMES = ["-", "\\", "|", "/"]

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def _run(self) -> None:
        for frame in itertools.cycle(self._FRAMES):
            if self._stop.is_set():
                break
            with self._lock:
                sys.stdout.write(f"\r  {frame} ")
                sys.stdout.flush()
            time.sleep(0.12)

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        with self._lock:
            sys.stdout.write("\r    \r")   # wipe the spinner frame
            sys.stdout.flush()

    def line(self, text: str) -> None:
        # Print a line above the spinner, clearing the current frame first.
        with self._lock:
            sys.stdout.write("\r" + text + "\n")
            sys.stdout.flush()


def _make_step_handler(spinner: _Spinner):
    # Live progress: each tool as it is called, for the orchestrator (ask_risk,
    # ask_optimization) and the nested specialist tools alike, since the handler
    # is threaded through deps. Printed through the spinner so they do not clash.
    async def handler(ctx, stream) -> None:
        async for event in stream:
            if isinstance(event, FunctionToolCallEvent):
                spinner.line(f"    ... {event.part.tool_name}")
    return handler


def _prompt_agent_menu() -> str:
    print("\nWhich agent?")
    for key, (_, label, desc) in _AGENT_CHOICES.items():
        tail = "  [Enter]" if key == "0" else ""
        print(f"  {key}  {label:<15} {desc}{tail}")
    return input("> ").strip() or "0"


def _resolve_agent(raw: str | None) -> tuple[str | None, str]:
    # Returns (mode, label). raw may be a digit, a name, or None (ask the menu).
    key = (raw if raw is not None else _prompt_agent_menu()).strip().lower()
    key = _AGENT_NAMES.get(key, key)
    mode, label, _ = _AGENT_CHOICES.get(key, _AGENT_CHOICES["0"])
    return mode, label


class _FakeHistoryProvider(HistoryProvider):
    """
    Deterministic seeded daily closes per ticker, no network.

    The per ticker seed is a stable hash, NOT Python's built in hash(), which is
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
        "--ai", dest="ai", default=None,
        help="model: provider shortcut (claude, openai, gemini, groq, mistral) or a "
             "full provider:name string. Overrides FINKRIT_MODEL.",
    )
    parser.add_argument(
        "-ag", "--agent", dest="agent", default=None,
        help="agent: 0 router (all), 1 risk, 2 optimization, 3 performance (or a name). "
             "Left off, a menu asks.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="do not print the live tool-call trace while the agent works.",
    )
    args = parser.parse_args(argv)

    if args.ai:
        model = _PROVIDER_DEFAULTS.get(args.ai.lower(), args.ai)
    else:
        model = os.environ.get("FINKRIT_MODEL", _DEFAULT_MODEL)
    _resolve_api_key(model)

    spinner = _Spinner()
    handler = None if args.quiet else _make_step_handler(spinner)
    assistant = Assistant(model=model, store=InMemoryStore(), registry=_registry(),
                          event_handler=handler)
    assistant.register_portfolio(make_fake_portfolio())

    mode, label = _resolve_agent(args.agent)
    prompt = "router" if mode is None else mode

    print("=" * 64)
    print(f"  finagent CLI   model: {model}   agent: {label}   (synthetic data)")
    print("=" * 64)
    print("  Holdings: " + ", ".join(f"{q} {t}" for t, q in _HOLDINGS.items()))
    print("  Ask about risk, performance, or the optimal allocation.")
    print("  Type 'quit' to exit.")

    while True:
        try:
            question = input(f"\n{prompt} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break
        spinner.start()
        try:
            answer = assistant.route(question) if mode is None else assistant.ask(question, agent=mode)
        except Exception as exc:  # noqa: BLE001 - a CLI should not crash on one bad turn
            spinner.stop()
            print(f"\nerror: {exc}")
            print("(if this is a model/auth error, set LLM_API_KEY and --ai)")
            continue
        spinner.stop()
        print(f"\nagent > {answer}")


if __name__ == "__main__":
    main()
