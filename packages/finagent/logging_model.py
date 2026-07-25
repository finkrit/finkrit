# finagent/logging_model.py
"""
Optional logging of every LLM request, for seeing exactly what the agent sends
to the model.

Off by default and enabled by the FINKRIT_LOG_LLM environment variable, because
the messages carry the system prompt, the user question, the tool definitions,
and the computed figures the tools return, none of which should land in logs
unless someone is deliberately debugging.

Implemented as a pydantic-ai WrapperModel: it logs the outgoing messages, then
delegates to the real model. Both the non-streaming path (request) and the
streaming path (request_stream, used when a live tool-call trace is attached)
are covered.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
from pydantic_ai.models.wrapper import WrapperModel


def _trim(value: Any, limit: int = 300) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def _part_summary(part: Any) -> str:
    # Render one message part (prompt, tool call, tool return, model text) as a
    # short readable line, tolerant of whatever part types pydantic-ai emits.
    name = type(part).__name__
    tool = getattr(part, "tool_name", None)
    if tool is not None:
        payload = getattr(part, "args", None)
        if payload is None:
            payload = getattr(part, "content", "")
        return f"{name}[{tool}] {_trim(payload)}"
    content = getattr(part, "content", None)
    if content is not None:
        return f"{name} {_trim(content)}"
    return name


def _log_request(model_name: str, messages: Any, params: Any) -> None:
    tools = [t.name for t in getattr(params, "function_tools", None) or []]
    logger.info(f"LLM request to {model_name}: {len(messages)} messages, tools={tools}")
    for message in messages:
        for part in getattr(message, "parts", []):
            logger.info(f"  send {_part_summary(part)}")


class LoggingModel(WrapperModel):
    """Wraps a model and logs the messages sent on every request."""

    async def request(self, messages, model_settings, model_request_parameters):
        _log_request(self.wrapped.model_name, messages, model_request_parameters)
        response = await self.wrapped.request(messages, model_settings, model_request_parameters)
        logger.info(f"LLM reply from {self.wrapped.model_name}: {[_part_summary(p) for p in response.parts]}")
        return response

    @asynccontextmanager
    async def request_stream(self, messages, model_settings, model_request_parameters, run_context=None):
        _log_request(self.wrapped.model_name, messages, model_request_parameters)
        async with self.wrapped.request_stream(
            messages, model_settings, model_request_parameters, run_context
        ) as stream:
            yield stream


def wrap_model_for_logging(model: Any) -> Any:
    """Wrap in a LoggingModel when FINKRIT_LOG_LLM is set, otherwise return the
    model unchanged. Accepts a Model, a model-name string, or None."""
    if model is None or not os.environ.get("FINKRIT_LOG_LLM"):
        return model
    return LoggingModel(model)
