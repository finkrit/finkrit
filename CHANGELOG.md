# Changelog

All notable changes to the finkrit packages are documented here. This repo ships
three independently versioned distributions, so each entry is headed by the
package and version it belongs to. The project follows semantic versioning.

Packages: `finkritq` (the quant core), `finkritintel` (the tool contracts), and
`finkrit` (the bundle that ships finagent, finkritserver, and the web app).

## [Unreleased]

### finkritq

### finkritintel

### finkrit

## finkrit 0.1.1 — 2026-07-26

### Fixed
- The dashboard chat now routes through the orchestrator, so performance and
  allocation questions reach a specialist instead of dead-ending at the risk
  agent, which had no return tools.
- The chat endpoint returns a 404 for a portfolio or asset miss and a 502 with a
  readable message for an agent run failure, instead of a raw 500 traceback.

### Added
- Data errors now surface to the model as a retry with the real reason, rather
  than arriving as silent nulls the model would explain incorrectly.
- Optional logging of every LLM request through the FINKRIT_LOG_LLM variable.
- A --url flag to point the agent at any OpenAI compatible local endpoint.

## finkritq 0.1.2 — 2026-07-26

### Fixed
- Drop the row for the latest not-yet-settled session, which yfinance returns
  with a NaN close. That single NaN propagated through the covariance and nulled
  out marginal contribution to risk for every holding.

### Added
- Loud logging of each fetch and its outcome, and of memoizer cache hits and
  misses, so an empty or slow fetch can be traced.
- Guards that fail with a clear error on degenerate data, too few overlapping
  observations or a non-finite close, instead of emitting NaN downstream.

## finkrit 0.1.0, finkritintel 0.1.0, finkritq 0.1.1 — 2026-07-23

### Added
- Initial public release. `pip install finkrit` installs the whole stack and the
  `finkrit` command, which starts the web dashboard or a terminal chat over a
  portfolio.
- `finkritq`, the deterministic quant core (risk, performance, optimization, and
  tax), published on its own with an optional live data provider.
- `finkritintel`, the framework neutral tool contracts that expose the core as
  callable capabilities.
- The finkrit bundle, which ships the finagent agents, the finkritserver API, and
  the built SvelteKit dashboard.
- Apache-2.0 license across the stack.
