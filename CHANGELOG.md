# Changelog

All notable changes to the finkrit packages are documented here. This repo ships
three independently versioned distributions, so each entry is headed by the
package and version it belongs to. The project follows semantic versioning.

Packages: `finkritq` (the quant core), `finkritintel` (the tool contracts), and
`finkrit` (the bundle that ships finagent, finkritserver, and the web app).

## [Unreleased]

### finkrit

#### Added
- A run reports what it is doing while it does it. Each step names the
  specialist that was asked and the sub question it was handed, then the tools
  it called, so a question that fans out across four specialists shows its work
  instead of sitting silent. The chat panel fills a list that settles as each
  specialist returns, and the terminal prints the same trace. Steps carry names
  and sub questions by default. Tool arguments and each specialist's verbatim
  answer are opt in, through `--steps` in the terminal, because those are the
  parts worth deciding about before they are written anywhere.

- The agents answer in one language, English unless told otherwise, set with
  `--lang` on either entry point. Nothing used to say, so a multilingual model
  was free to choose and would answer in another language from one question to
  the next. The setting reaches every specialist as well as the orchestrator,
  since the orchestrator combines their replies as they came back and one
  specialist is enough to make a reply bilingual. Tickers, numbers, and dates
  are explicitly held back from translation.

- `--logs` turns on the library log stream, off by default. The spinner and the
  step trace both redraw a single line, and a debug log arriving mid redraw
  tears it, so the terminal stays quiet unless the flag asks otherwise. Every
  flag on both entry points now carries its own line in `--help`.

- `--truncate-steps` cuts each step to one terminal row. Steps print whole by
  default, since the reason to ask for detail is to read what a specialist was
  asked and what it said back, and a cut falls on exactly that. The flag is
  there for a narrow terminal or a wide fan out, where wrapped lines bury the
  shape of the trace.

#### Changed
- A lookup that misses now names what is registered, not only what is missing.
  "No asset registered with ticker X" is true of the argument but reads as a
  claim about the portfolio, and a model with no way to list its holdings will
  believe it. One told the user their portfolio was empty directly underneath
  a beta it had just computed from twelve holdings. The message now lists the
  real tickers, so a retry can land on one, and only a genuinely empty store
  reads as empty. An invented argument is trimmed before it is echoed back,
  because a model that guesses a ticker can guess something arbitrarily long.

- The tool budget is now two budgets rather than one shared number. The
  orchestrator's tools are the four specialists, so its ceiling counts
  delegations and sits at eight: enough to ask all four and go back to one,
  low enough that a ninth is a loop rather than thoroughness. A specialist's
  ceiling counts metrics and sits at twelve, which covers the widest honest
  risk question with room left to correct a rejected call. The request ceiling
  is derived from the tool ceiling instead of being guessed, so a run that
  dies reports how much work it attempted rather than how many times it spoke
  to the model. One number governing both meant the orchestrator was
  effectively unbounded while a wide risk question could clip.

- A rejected tool call gets two chances to be corrected instead of one, and
  the trace now prints the reason it was rejected. A strong model rarely needs
  the second chance. A local one will get an enum or a ticker wrong twice
  before it reads the error, and the run used to die with nothing on screen
  but the retry count. The tool budget above stays the real backstop.

#### Fixed
- A local model name is no longer split at its own colon. An Ollama tag is
  family and size, so `qwen2.5:14b` reached the endpoint as `14b` and came back
  404. Only a prefix pydantic-ai recognises as a provider is stripped now, so
  `openai:gpt-5` still arrives as `gpt-5` and any local tag arrives whole.

- `./run cli` reaches the terminal chat. The bootstrap jumped straight to the
  web launcher and skipped the subcommand dispatcher, so `cli` arrived at the
  web app's argument parser as a stray flag and a source checkout could open
  the dashboard but never the terminal. `./run` and `./run --dev` are
  unchanged, since no subcommand still means web.

## finkritq 0.4.0 — 2026-08-03

### Added
- `long_term_transitions`: the short term lots approaching the 365 day
  boundary, each with its signed unrealized gain and the days remaining. The
  boundary cuts both ways, a gain lot is worth holding across it and a loss
  lot is worth harvesting before it, so the scan reports the facts and the
  caller reads the sign.
- `MemoizingSnapshotProvider`, a short TTL cache over spot quotes. History was
  memoized but snapshots were not, so every tax question re-downloaded one
  quote per holding. Sixty seconds covers one dashboard interaction reading a
  consistent price without going stale across interactions.

### Changed
- `RestrictionKind` members carry explicit string values instead of `auto()`.
  auto() numbers by definition order, so inserting or reordering a member
  silently renumbers everything ever serialized. Comparisons are identity
  based throughout the package and are unaffected, but the serialized form
  changes from an integer to a string. **Breaking** for anyone who persisted
  the old numeric values. The minor version carries it, since under semantic
  versioning a 0.x break bumps there.

## finkritintel 0.2.1 — 2026-08-03

### Changed
- Spot prices are fetched in parallel, one worker per holding, matching the
  history fan out. The sequential loop made every tax tool wait holdings times
  latency. The helper is public as `spot_prices` now, so the layers above can
  price against the same quote source.

## finkrit 0.1.5 — 2026-08-03

### Added
- Two dashboard views with no LLM anywhere in their path. Tax signals shows
  what to act on today priced in dollars: lots worth harvesting with the
  estimated saving at assumed (and adjustable) rates, wash sale warnings, and
  long term countdowns that say hold or act per lot. Rebalance lays the three
  strategies side by side over one shared target, each with its tax cost,
  harvested loss, and residual drift, with the sells of the selected strategy
  itemized per lot method.
- Downloads are visible and parallel. A prefetch endpoint warms the price
  caches with one worker per ticker and streams progress, and the dashboard
  shows it as an overlay with a live bar and a chip per stock lighting up as
  each download lands.
- Beta questions no longer stall on "which benchmark?". The compiled tools
  default to the S&P 500 (^GSPC) when no benchmark is named, the default is
  stated in each tool's description, and the risk specialist is instructed to
  use it and say so rather than asking.

### Fixed
- Switching dashboard views no longer refetches everything. Results are held
  for the session and refresh on demand or when a new portfolio is saved,
  instead of every visit re-downloading data that had not changed.

## finkritq 0.3.0 — 2026-07-29

### Added
- Two ways to spend less tax on the same rebalance, both composable with the
  gain budget. `RebalanceSizing.TO_BAND_EDGE` sells only the excess beyond the
  tolerance band instead of the full drift (and refuses to run without a band,
  since the edge would be the target). Partial fill scales a budget-breaching
  sell down to a prefix of its lot order that exactly exhausts the remaining
  gain room, instead of deferring it whole, built on a new
  `select_lots_to_sell_within_gain` that never realizes lots out of the
  elected order.
- Every tax rebalance plan now reports `residual_drift`, the overweight still
  held after its sells. It is the tracking cost a plan paid for its tax bill,
  which is what makes plans with different strategies comparable.
- `compare_rebalance_strategies` runs the same rebalance under the named
  strategy menu (full, band_edge, partial_fill) with everything else held
  constant, returning the plans side by side.

## finkritintel 0.2.0 — 2026-07-29

### Added
- A tax-aware rebalance tool on the optimization capability, the composition
  the tax contracts pointed at. It computes target weights from the chosen
  objective (minimum variance or maximum Sharpe), then realizes the overweight
  sells drift first under a capital gains budget: losses always, gains until
  the budget, the rest deferred and named. Lots are picked by sale method,
  HIFO by default, sized to target or to the band edge, with optional partial
  fills that spend the budget to the dollar. The whole chain runs in code, the
  model supplies only the knobs and narrates the plan. Proposes, never trades.
- A strategy comparison tool that runs the same rebalance under the fixed
  three-strategy menu and returns the plans side by side, each with its
  realized gain, harvested loss, and residual drift, so the tradeoff between
  tax cost and remaining drift is visible in one table.

## finkrit 0.1.4 — 2026-07-29

### Added
- An example portfolio ships with the package. `finkrit cli --file example`
  loads a twelve position, sixteen lot sample shaped like a real custodian
  export, so a fresh install has something to run against without authoring a
  CSV first. The README walks through it, leading with the case a blended cost
  basis hides.
- The optimization specialist can propose tax-aware rebalancing. Ask what
  rebalancing would cost in tax, or what a given gain budget buys, and it
  reports the plan with the realized gain split long versus short term and
  the sells a bigger budget would unlock. Ask to weigh options and it lays the
  three strategies side by side with what each costs in tax and leaves in
  drift.

## finkritq 0.2.0 — 2026-07-28

### Changed
- `LotSaleMethod` moves to `finkritq.datatype`, where the other method enums
  live, and is importable from there. The old
  `finkritq.optimize.lotselection.LotSaleMethod` path still works.
- `flows_to_series` moves out of `finkritq.datatype` to
  `finkritq.anal.performance`, beside the two functions that consume its output.
  It converts one representation into another rather than naming a concept, so
  it is a transform and that package holds vocabulary. `CashFlow` itself stays.
  **Breaking** for anyone importing it from `finkritq.datatype`. The minor
  version carries it, since under semantic versioning a 0.x break bumps there.

## finkrit 0.1.3 — 2026-07-28

### Added
- A portfolio can hold several tax lots per ticker. A CSV row is now one lot, so
  repeating a ticker describes a position built from several purchases, which is
  how a brokerage export reads. Each lot keeps its own cost and acquisition date
  through the upload, the chat CLI, and the analytics.
- The holdings table shows one row per position rather than one per lot. A
  ticker bought several times reads as a single holding with its blended cost
  per share, and expands from the chevron or the ticker to show each purchase
  with its own cost, date, and share of the position. One control in the header
  opens or closes every position at once.
- The specialist pills on a reply are now clickable. Opening one shows the
  sub-question the orchestrator handed that specialist and the answer it gave
  back, verbatim, so a combined reply can be checked against what each domain
  actually said rather than taken on faith. Read off the agent run, not off the
  final text.

### Fixed
- The README, which is the PyPI page, had gone stale: it said three specialists
  when there are four, offered `-ag 0|1|2|3` with no tax agent, and listed half
  the CSV column names the loader accepts. A test now reads the agent registry
  and the alias tables out of the code and fails the suite when the README
  disagrees, so the published description cannot silently drift again.
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
