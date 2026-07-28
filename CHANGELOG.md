# Changelog

All notable changes to the finkrit packages are documented here. This repo ships
three independently versioned distributions, so each entry is headed by the
package and version it belongs to. The project follows semantic versioning.

Packages: `finkritq` (the quant core), `finkritintel` (the tool contracts), and
`finkrit` (the bundle that ships finagent, finkritserver, and the web app).

## [Unreleased]

### finkrit

#### Added
- A portfolio can hold several tax lots per ticker. A CSV row is now one lot, so
  repeating a ticker describes a position built from several purchases, which is
  how a brokerage export reads. Each lot keeps its own cost and acquisition date
  through the upload, the chat CLI, and the analytics.

#### Fixed
- Harvesting and the holding period split now see the individual lots. Every
  holding used to collapse to a single blended lot, which hid underwater lots
  behind a position that was up overall, so the losses actually worth harvesting
  never showed up.

## finkritintel 0.1.1 — 2026-07-27

### Added
- A tax capability exposing the read-only tax lens as callable tools: unrealized
  gains and losses at current prices, tax-loss harvesting candidates net of the
  wash sale window, and the long versus short term split of the portfolio.
- The tax bindings read current prices from the snapshot provider and fall back
  to the most recent history close when no snapshot provider is registered, so
  they work against an offline registry as well as a live one.

## finkrit 0.1.2 — 2026-07-27

### Fixed
- The wheel was missing three modules, so the installed command could not start.
  `finagent/logging_model.py` is imported unconditionally by the assistant, and
  0.1.1 shipped without it. `finagent/conversation.py` and
  `finkritserver/conversations.py` were absent for the same reason. A test now
  reads the wheel manifest and fails when a module exists on disk but is not
  packaged.
- The floor on finkritintel is now 0.1.1, the version that actually carries the
  tax capability finagent imports. The looser pin would let a resolver install
  0.1.0 and fail on that import.

### Added
- A tax specialist in the chat. Ask about unrealized gains, what is harvestable
  before year end, or how much of the portfolio qualifies for long term
  treatment. Reachable directly as agent 4 in the CLI (`-ag tax`) and through the
  orchestrator, which now fans a mixed question out across all four specialists.
  The specialist is read-only, it describes the tax position and never trades.
- The chat remembers the conversation, so a follow up like "and how does that
  compare" keeps its context. Threads are held per conversation id, bounded, and
  can be reset.
- Replies show which specialists answered them, read off the tools the
  orchestrator actually called rather than anything the model claims.
- The chat panel can be resized by dragging or with the arrow keys, and
  remembers its width.

### Changed
- The dashboard type is now driven by a single root size rather than pixel
  values spread across every component, and reads larger.

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
