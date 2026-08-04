# finagent/cli.py
"""
Interactive CLI: a seeded fake portfolio and a chat loop against the agent.

No network, a deterministic fake price provider stands in for the live data
feed, so the numbers are reproducible and nothing is downloaded. The agent
itself is real and needs a model plus its API key in the environment.

    LLM_API_KEY=... python -m finagent --model openai
    LLM_API_KEY=... python -m finagent --model claude -ag 1
    LLM_API_KEY=... python -m finagent --model openai -ag 0

--model picks the model, a provider shortcut (claude, openai, gemini, groq,
mistral) or a full provider:name string, keyed by a generic LLM_API_KEY mapped
onto whatever env var the provider expects. -ag picks the agent: 0 the
all-encompassing router, 1 risk, 2 optimization, 3 performance, 4 tax. Left off,
a menu asks. Type a question, or 'quit' to leave.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import os
import sys
import threading
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np

from finkritq.asset import Asset, Stock
from finkritq.data import DataRegistry
from finkritq.data.interfaces import HistoryProvider
from finkritq.datatype import Currency, Exchange, PriceHistory
from finkritq.portfolio import Portfolio, Position, TaxLot

from finagent.agent.base import DEFAULT_LANGUAGE
from finagent.assistant import Assistant
from finagent.ingest import csv_date, csv_number, csv_value
from finagent.progress import Step, StepDetail, StepKind, StepStatus, progress_handler
from finagent.store import DEFAULT_PORTFOLIO_ID, InMemoryStore

_DEFAULT_MODEL = "anthropic:claude-sonnet-5"
_HOLDINGS = {"AAPL": "40", "MSFT": "30", "NVDA": "20", "JPM": "25", "XOM": "35"}

# Provider shortcuts for `--model`. Each maps to a sensible default model, and
# a full provider:name string to --model or FINKRIT_MODEL picks an exact one.
# pydantic-ai handles every provider behind the same interface, so switching is
# just the model string.
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


def configure_logging(verbose: bool) -> None:
    """Quiet finkritq's data logs unless they were asked for.

    finkritq logs every fetch, cache hit, and cache miss through loguru, which
    ships a stderr sink at DEBUG, so a single question emits dozens of lines.
    They also interleave with the spinner and the step trace, both of which
    redraw one line, so the output is not merely noisy, it is corrupted.

    WARNING and above still print, because an empty fetch or a rate limit is
    the thing you most need to see and the least likely to guess at.

    loguru arrives with finkritq's data extra. Without it there are no data
    logs to configure, so a missing import is nothing to report.
    """
    try:
        from loguru import logger
    except ImportError:
        return
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING")


def local_model_name(model_string: str) -> str:
    """The model name to send to an OpenAI-compatible endpoint.

    A cloud model is named ``provider:name`` and only ``name`` belongs on the
    wire, so ``openai:gpt-5`` has to become ``gpt-5``. But a local model's own
    name routinely contains a colon: Ollama tags are ``family:size``, so
    ``qwen2.5:14b`` is the whole name and splitting it asks the server for a
    model called ``14b``, which 404s.

    The two cases are told apart by asking pydantic-ai whether the prefix is
    actually a provider it knows. That stays correct as providers are added,
    where a hardcoded list would rot. Anything else is passed through whole.
    """
    prefix, separator, rest = model_string.partition(":")
    if not separator:
        return model_string
    from pydantic_ai.providers import infer_provider_class

    try:
        infer_provider_class(prefix)
    except Exception:  # noqa: BLE001 - not a provider name, so not a prefix
        return model_string
    return rest


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
    "4": ("tax", "Tax", "unrealized gains, harvestable losses, holding period"),
}
_AGENT_NAMES = {
    "all": "0", "router": "0", "risk": "1",
    "optimization": "2", "optimize": "2", "opt": "2", "performance": "3", "perf": "3",
    "tax": "4",
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


# How much of a step to show when the trace is truncated. A sub question, a
# specialist's answer, and a retry reason are all prose and run long. Tool
# arguments sit at the deepest indent and share their line with the tool name,
# so they get less room than the prose does.
_PROSE_WIDTH = 60
_ARGS_WIDTH = 50


def _clip(text: str, width: int | None) -> str:
    """``text`` on one line, cut to ``width``. ``None`` means do not cut.

    The flattening happens either way. Widths are a readability choice, but a
    newline is not: the spinner redraws a single line, so a step carrying a
    second one would strand the first on screen.
    """
    flat = " ".join(str(text).split())
    if width is None or len(flat) <= width:
        return flat
    return flat[: width - 1] + "…"


def _because(step: Step, width: int | None) -> str:
    # Only carried at StepDetail.FULL, so without --steps a retry still shows
    # that it happened, just not why.
    return f": {_clip(step.content, width)}" if step.content else ""


def _render(step: Step, truncate: bool = False) -> str | None:
    """One trace line for a step, or None for the ones not worth a line.

    A specialist gets both its start and its finish, since the wait between
    them is the thing the reader is sitting through. A tool gets only its
    start: showing both doubles the trace to say nothing new, because the
    answer that follows is the evidence it returned.

    ``truncate`` cuts the long values so every step stays within one terminal
    row. Off by default, because the reason to ask for detail at all is to read
    what a specialist was asked and what it said back, and the cut falls on
    exactly that. Turn it on when the trace matters less than its shape, on a
    narrow terminal or a run that fans out wide, where wrapped lines bury the
    structure the trace exists to show.
    """
    prose = _PROSE_WIDTH if truncate else None
    # A retry carries the reason the tool refused, which is the whole value of
    # showing it: "retrying" alone says something went wrong and nothing about
    # what, and a run that dies on exhausted retries leaves no other trace.
    if step.kind is StepKind.SPECIALIST:
        if step.status is StepStatus.STARTED:
            asked = f": {_clip(step.detail, prose)}" if step.detail else ""
            return f"  → asking {step.name}{asked}"
        if step.status is StepStatus.RETRY:
            return f"  ⟳ {step.name} retrying{_because(step, prose)}"
        answer = f"  {_clip(step.content, prose)}" if step.content else ""
        return f"  ✓ {step.name} answered{answer}"

    if step.status is StepStatus.RETRY:
        return f"      ⟳ {step.name} retrying{_because(step, prose)}"
    if step.status is StepStatus.STARTED:
        shown = {k: v for k, v in step.args.items() if k != "portfolio_id"}
        joined = ", ".join(f"{k}={v}" for k, v in shown.items())
        detail = f"  {_clip(joined, _ARGS_WIDTH if truncate else None)}" if shown else ""
        return f"      · {step.name}{detail}"
    return None


def _make_step_handler(spinner: _Spinner, detail: StepDetail, truncate: bool = False):
    # Live progress for the orchestrator's delegations and the nested
    # specialists' own tools alike, since the handler is threaded through deps.
    # Printed through the spinner so a step and a spinner frame never collide.
    def show(step: Step) -> None:
        line = _render(step, truncate)
        if line is not None:
            spinner.line(line)

    return progress_handler(show, detail)


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


# `--file example` loads the bundled sample instead of a path. Installing from
# PyPI leaves a user with nothing to point --file at, and hand authoring a CSV
# before you can see anything is a poor first five minutes. The file ships
# inside the package so this resolves the same way from a source checkout and
# from a wheel.
EXAMPLE = "example"


def example_portfolio_path() -> str:
    """Filesystem path to the bundled example portfolio."""
    from importlib.resources import files

    path = files("finagent") / "examples" / "portfolio.csv"
    if not path.is_file():
        raise ValueError(
            "The bundled example portfolio is missing from this install. "
            "Pass a path to your own CSV with --file instead."
        )
    return str(path)


# A date for a lot whose file gave none. The CLI substitutes and carries on,
# where the upload path records it for the user to correct, because a chat
# session is throwaway and a saved portfolio is not.
CSV_FALLBACK_ACQUIRED = date(2022, 1, 3)


def _load_portfolio_from_csv(path: str, portfolio_id: str = DEFAULT_PORTFOLIO_ID) -> Portfolio:
    """Build a portfolio from a CSV. Recognizes common column names for ticker,
    quantity, cost per share, and acquired date, so a typical brokerage export
    loads without editing. A missing cost or date falls back to a default.

    Column aliases, date layouts, and the number cleaning live in finagent.ingest
    and are shared with the upload path, so a new spelling taught to one is
    understood by both. What differs is the response to a gap: here a default is
    substituted silently, there it becomes a note the user is asked to check.
    """
    # One row is one tax lot. A ticker bought several times appears on several
    # rows, and those become several lots under one position, which is what the
    # tax analytics need in order to have lots to choose between. Insertion
    # ordered, so positions keep the order the file listed them in.
    lots_by_ticker: dict[str, list[TaxLot]] = {}
    with open(path, newline="") as handle:
        for i, row in enumerate(csv.DictReader(handle)):
            ticker = csv_value(row, "ticker")
            if not ticker:
                continue
            ticker = ticker.upper()
            quantity = csv_number(csv_value(row, "quantity"))
            cost = csv_number(csv_value(row, "cost_per_share"))
            acquired = csv_date(csv_value(row, "acquired")) or CSV_FALLBACK_ACQUIRED
            lot = TaxLot(id=f"lot-{i}", quantity=Decimal(quantity),
                         cost_per_share=Decimal(cost), acquired=acquired)
            lots_by_ticker.setdefault(ticker, []).append(lot)

    positions = [
        Position(
            id=f"pos-{index}",
            asset=Stock(ticker=ticker, currency=Currency.USD,
                        exchange=Exchange.NASDAQ, company_name=f"{ticker} Corp"),
            lots=tuple(lots),
        )
        for index, (ticker, lots) in enumerate(lots_by_ticker.items())
    ]
    if not positions:
        raise ValueError(
            f"No holdings found in {path}. Expect columns like ticker, quantity, cost, acquired."
        )
    return Portfolio(id=portfolio_id, name="Portfolio from CSV", positions=positions)


def _registry() -> DataRegistry:
    registry = DataRegistry()
    registry.register_history(_FakeHistoryProvider())
    return registry


def _real_registry() -> DataRegistry:
    # Live market data, memoized per session, for a real portfolio loaded from a
    # file. The fake seeded provider only makes sense for the demo portfolio.
    from finkritq.data.providers import MemoizingHistoryProvider, YFinanceProvider

    registry = DataRegistry()
    registry.register_history(MemoizingHistoryProvider(YFinanceProvider()))
    registry.register_snapshot(YFinanceProvider())
    return registry


def _print_holdings(portfolio: Portfolio) -> None:
    # Print the loaded holdings so the user can confirm what was parsed.
    print(f"  {'Ticker':<8}{'Qty':>10}{'Cost/Share':>14}{'Acquired':>14}")
    for pos in portfolio.positions:
        qty = sum(lot.quantity for lot in pos.lots)
        lot = pos.lots[0]
        print(f"  {pos.asset.ticker:<8}{qty:>10g}{float(lot.cost_per_share):>14.2f}{str(lot.acquired):>14}")


def build_parser() -> argparse.ArgumentParser:
    """The CLI's flags, separate from main so they can be parsed in a test.

    Worth the split for one flag in particular: --ai is a released name kept
    alive by a second, suppressed argument sharing --model's destination, and
    nothing about reading that line proves the value actually lands.
    """
    parser = argparse.ArgumentParser(
        prog="python -m finagent",
        description="Chat with the portfolio agent over a seeded fake portfolio.",
    )
    parser.add_argument(
        "--model", dest="model", default=None,
        help="model: provider shortcut (claude, openai, gemini, groq, mistral) or a "
             "full provider:name string, or the served name behind --url. "
             "Overrides FINKRIT_MODEL.",
    )
    # The released name for the same flag, still accepted so existing scripts
    # and shell history keep working. Suppressed from --help: one name to
    # learn, and --model is the one the web entry point already used.
    parser.add_argument("--ai", dest="model", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "-ag", "--agent", dest="agent", default=None,
        help="agent: 0 router (all), 1 risk, 2 optimization, 3 performance, 4 tax "
             "(or a name). Left off, a menu asks.",
    )
    parser.add_argument(
        "-f", "--file", dest="file", default=None,
        help="path to a portfolio CSV (ticker, quantity, cost, acquired), or "
             "'example' for the bundled multi-lot sample. Left off, a seeded fake "
             "portfolio is used. With a file, live prices are used.",
    )
    parser.add_argument(
        "--key", dest="key", default=None,
        help="LLM API key, an alternative to the LLM_API_KEY env var.",
    )
    parser.add_argument(
        "--url", dest="url", default=None,
        help="base url of an OpenAI-compatible endpoint (a local Ollama, LM Studio, "
             "vLLM, or self-hosted server). No key needed. Set --model to the served name.",
    )
    parser.add_argument(
        "--lang", dest="lang", default=DEFAULT_LANGUAGE,
        help=f"language to answer in, as a plain name ({DEFAULT_LANGUAGE} by "
             f"default). Multilingual local models otherwise pick for "
             f"themselves, often inconsistently.",
    )
    parser.add_argument(
        "--logs", action="store_true",
        help="print finkritq's data fetch logs, every download and cache hit. "
             "Off by default because they interleave with the step trace and "
             "corrupt it. Warnings and errors print either way.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="do not print the live step trace while the agent works.",
    )
    parser.add_argument(
        "--steps", action="store_true",
        help="show more of each step: the arguments a tool was called with and "
             "the answer each specialist returned, as they happen. Off by "
             "default, and ignored with --quiet.",
    )
    parser.add_argument(
        "--truncate-steps", dest="truncate_steps", action="store_true",
        help="cut each step to one terminal row instead of printing it whole. "
             "Only affects what --steps adds, since that is the only part long "
             "enough to wrap. Useful on a narrow terminal or a wide fan out, "
             "where wrapping buries the shape of the trace.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    # Before anything can fetch, so the first download is already quiet.
    configure_logging(args.logs)

    if args.key:
        os.environ["LLM_API_KEY"] = args.key

    model: object
    if args.model:
        model = _PROVIDER_DEFAULTS.get(args.model.lower(), args.model)
    else:
        model = os.environ.get("FINKRIT_MODEL", _DEFAULT_MODEL)

    if args.url:
        # Any OpenAI-compatible local or self-hosted endpoint. Local servers
        # ignore the key, so a placeholder is fine.
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        key = os.environ.get("LLM_API_KEY") or os.environ.get("LLM_KEY") or "local"
        model = OpenAIChatModel(
            local_model_name(model),
            provider=OpenAIProvider(base_url=args.url, api_key=key),
        )
    else:
        _resolve_api_key(model)

    # A file means a real portfolio with live prices. No file means the seeded
    # offline demo. The two data sources are not mixed.
    if args.file:
        path = example_portfolio_path() if args.file == EXAMPLE else args.file
        portfolio = _load_portfolio_from_csv(path)
        registry = _real_registry()
        source = f"live data, {path}"
    else:
        portfolio = make_fake_portfolio()
        registry = _registry()
        source = "synthetic data"

    spinner = _Spinner()
    # --quiet wins over --steps: asking for silence and for detail at once is a
    # contradiction, and silence is the safer reading of it.
    handler = None if args.quiet else _make_step_handler(
        spinner,
        StepDetail.FULL if args.steps else StepDetail.SUMMARY,
        args.truncate_steps,
    )
    assistant = Assistant(model=model, store=InMemoryStore(), registry=registry,
                          event_handler=handler, language=args.lang)
    assistant.register_portfolio(portfolio)

    mode, label = _resolve_agent(args.agent)
    prompt = "router" if mode is None else mode

    print("=" * 64)
    print(f"  finagent CLI   model: {model}   agent: {label}   ({source})")
    print("=" * 64)
    if args.file:
        print(f"  Loaded {len(portfolio.positions)} holdings from {args.file}")
    _print_holdings(portfolio)
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
            print("(if this is a model/auth error, set LLM_API_KEY and --model)")
            continue
        spinner.stop()
        print(f"\nagent > {answer}")


if __name__ == "__main__":
    main()
