# finagent/tests/test_ingest.py
"""
Tests for CSV -> ParsedPortfolio extraction. Structured output_type in
pydantic-ai is implemented as a hidden tool call named "final_result"
(verified via AgentInfo.output_tools, not guessed) -- so a scripted
FunctionModel returns a ToolCallPart targeting that tool with the parsed
JSON as args, simulating what a real model does after reading the CSV text.
"""
from __future__ import annotations

import asyncio
import warnings

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from finagent.ingest import ParsedPortfolio, parse_portfolio_csv, parse_portfolio_csv_async

warnings.filterwarnings("ignore", message="Could not generate return schema")

_PARSED_ARGS = {
    "name": "Uploaded Portfolio",
    "holdings": [
        {
            "ticker": "AAPL",
            "quantity": 10,
            "cost_per_share": 150.0,
            "acquired": "2023-01-15",
            "exchange": "NASDAQ",
            "currency": "USD",
            "confidence_note": None,
        }
    ],
    "warnings": ["Assumed 'Avg Cost' column was per-share, not total."],
}


def _script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(tool_name="final_result", args=_PARSED_ARGS)])


class TestParsePortfolioCsv:

    def test_returns_parsed_portfolio(self):
        result = parse_portfolio_csv("Symbol,Shares\nAAPL,10", model=FunctionModel(_script))
        assert isinstance(result, ParsedPortfolio)
        assert result.name == "Uploaded Portfolio"

    def test_holdings_mapped(self):
        result = parse_portfolio_csv("Symbol,Shares\nAAPL,10", model=FunctionModel(_script))
        assert len(result.holdings) == 1
        holding = result.holdings[0]
        assert holding.ticker == "AAPL"
        assert holding.quantity == 10
        assert str(holding.acquired) == "2023-01-15"

    def test_warnings_surfaced_for_user_review(self):
        result = parse_portfolio_csv("Symbol,Shares\nAAPL,10", model=FunctionModel(_script))
        assert result.warnings == ["Assumed 'Avg Cost' column was per-share, not total."]

    def test_async_matches_sync(self):
        result = asyncio.run(
            parse_portfolio_csv_async("Symbol,Shares\nAAPL,10", model=FunctionModel(_script))
        )
        assert result.holdings[0].ticker == "AAPL"


class TestParsedPortfolioDefaults:

    def test_no_holdings_or_warnings_defaults_empty(self):
        p = ParsedPortfolio(name="Empty")
        assert p.holdings == []
        assert p.warnings == []
