# Changelog

All notable changes to the finkrit packages are documented here. This repo ships
three independently versioned distributions, so each entry is headed by the
package and version it belongs to. The project follows semantic versioning.

Packages: `finkritq` (the quant core), `finkritintel` (the tool contracts), and
`finkrit` (the bundle that ships finkritcore, finagent, finkritserver, and the
web app).

## [Unreleased]

### finkritq

#### Added
- `RiskMetric` in `finkritq.datatype`: the names of the risk metrics the stack
  computes, moved down from the report layer above, plus the portfolio-only
  classification (`PORTFOLIO_ONLY_METRICS`, `asset_metrics`). Contribution
  metrics decompose risk across holdings, so a single asset has nothing to
  decompose, and that is a fact about the metrics rather than about any one
  report. Moved for the same reason `LotSaleMethod` lives here: the layers
  that need the shared names, report composition and the tool contracts, do
  not import each other, so the vocabulary sits at the one layer everything
  imports. The quant functions themselves are unchanged, one function per
  metric, and take no `RiskMetric`. The curated selections (`CORE`, `ALL`,
  the `"core"`/`"all"` aliases) deliberately stay in the report layer, which
  re-exports `RiskMetric`, so which metrics a PM sees first remains a product
  opinion rather than a math fact.

### finkritintel

#### Changed
- The risk capability is two tools instead of twenty. Nine metrics across two
  scopes made twenty near identical descriptions carrying eleven ideas, and
  every asset tool took a single ticker, so "the betas of my holdings" was one
  call per holding. `portfolio_risk` and `asset_risk` each take a list of
  metrics, and `asset_risk` takes a list of tickers that defaults to every
  holding. That default is the important half: the agent holds an opaque
  portfolio id and can only ever learn a ticker by receiving one in a result,
  so left to itself it invented them. Resolving holdings in code keeps that
  lookup on the correct side of the boundary rather than putting the holdings
  list in a prompt. A per holding question now costs one call at twelve
  holdings and one at two hundred.

  Omitting `metrics` computes every metric rather than a curated few. A model
  that fumbles the list gets a superset of what was asked, which is wasteful
  and never wrong, where a curated default would return metrics that exclude
  what was asked and be narrated as though they answered it. Every result names
  what it `computed` and what was `available` but not requested, so a model can
  narrow on a second call instead of mistaking an incomplete answer for a whole
  one. Values carry six significant figures, since rounding a ratio to three
  decimals renders 28.40% where the dashboard, formatting the unrounded float,
  says 28.41%. A call covering more holdings than the per call cap says how
  many it left out rather than truncating silently.

  The per metric bindings are unchanged and still exported. They are what these
  two call, and they still serve the dashboard's report composer. They are
  simply no longer doors a model opens directly.

- Every risk result now says what its numbers mean and what period they cover.
  It used to send bare floats and an `interval` field, leaving a model to infer
  the rest, and a small one infers confidently. One run reported Value at Risk,
  which is a fraction, as `$204.77` per holding and `$1,014` for the portfolio,
  figures that would need position values it was never given. The same run
  reported every beta as "over past 1 day interval", reading the sampling
  frequency as the lookback. Results now carry a `window` with real start and
  end dates alongside a separately named `sampling`, and a `units` line for
  each metric saying plainly that a fraction is a fraction and not a currency
  amount. Same principle as the `computed`/`available` keys: never leave a gap,
  because a model fills gaps rather than asking.

- Results carry the security's own name when the file gave one. A model handed
  a bare ticker supplies a company name from memory, and one run labelled `V`
  as "Vanguard Utilities ETF" when it is Visa.

### finkrit

#### Changed
- A CSV's security name is read and kept. Most exports print the company beside
  the symbol in a `Description` column, and that column was parsed and thrown
  away, storing `AAPL Corp` where the file said `APPLE INC`. It is now read
  under any of `description`, `name`, `security`, `security name`, `company`, or
  `company name`, and reaches the agent so it never has to remember one. Still
  optional: a file without it loads exactly as before, since a name improves an
  answer rather than making one possible.

- A question answered by one specialist reaches you in that specialist's own
  words. There is nothing to combine, so the orchestrator's closing text was a
  second pass restating content it was told not to alter: the longest prose in
  the run, written last, over numbers it had to copy exactly. Both failures
  seen on a local model took that shape. One restated a beta as -0.05 where the
  specialist had said -0.06, and one summarized a Chinese answer into Thai
  while instructed in English, following the content rather than the
  instruction. Passing the answer through makes both impossible rather than
  unlikely, and saves a generation. A question that genuinely spans specialists
  is still combined, because there the synthesis is the work.

- The deterministic layer is its own package, `finkritcore`. The `Store`, the
  report composers, the deterministic CSV mapper, and a new `Desk`
  facade moved out of finagent, which now composes them with the agents rather
  than containing them. Behaviour is unchanged and the bundle still ships
  everything, but the dashboard's entire path now exists without pydantic-ai,
  which is the shape the analytics need in order to be embeddable on their own
  and the shape the compliance boundary already assumed. A new layering test
  fails the suite if a lower layer ever imports an upper one.

  **Breaking** for imports: `finagent.store` and `finagent.report` are now
  `finkritcore.store` and `finkritcore.report`, and `CSV_ALIASES` moved again,
  from `finagent.ingest` to `finkritcore.ingest`. `finagent.ingest` still
  re-exports `ParsedPortfolio` and `ParsedHolding`, because they are the return
  types of the model fallback that stayed there.

## finkrit 0.2.0 — 2026-08-04

The minor rather than a patch: `CSV_ALIASES` and `CSV_DATE_FORMATS` moved from
`finagent.cli` to `finagent.ingest`, which breaks an import for anyone who
reached for them at the old address, and under semantic versioning a 0.x break
bumps here. Nothing else in this release is breaking. `--ai` still parses,
every endpoint that existed still exists, and `finkritq` and `finkritintel` are
unchanged at 0.4.0 and 0.2.1.

### Added
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

### Changed
- A CSV upload whose header names its columns is read in code, not by a model.
  Every upload used to be a one shot LLM extraction, which a hosted model
  answers in a second or two and a local one answers in minutes, with a blank
  screen throughout. The bundled sample now parses in under a millisecond with
  no model and no key, and only a file that leaves the ticker, quantity, cost
  per share, or acquired date unnamed still needs one. The alias table and date
  formats moved to `finagent.ingest` and are shared with the terminal loader,
  so a new spelling taught to one is understood by both. Where they differ is
  the response to a gap: the terminal substitutes a default silently, the
  upload records it on the holding for the user to correct.

- The model flag is `--model` on both entry points. The terminal called it
  `--ai` and the web app called it `--model`, so the same idea had two names
  and the wrong one was a parse error rather than a hint. `--ai` still works
  and is no longer advertised, so nothing anyone already typed breaks.

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

### Fixed
- A local model name is no longer split at its own colon. An Ollama tag is
  family and size, so `qwen2.5:14b` reached the endpoint as `14b` and came back
  404. Only a prefix pydantic-ai recognises as a provider is stripped now, so
  `openai:gpt-5` still arrives as `gpt-5` and any local tag arrives whole.

- `./run cli` reaches the terminal chat. The bootstrap jumped straight to the
  web launcher and skipped the subcommand dispatcher, so `cli` arrived at the
  web app's argument parser as a stray flag and a source checkout could open
  the dashboard but never the terminal. `./run` and `./run --dev` are
  unchanged, since no subcommand still means web.

- The source distribution no longer ships the web app's `node_modules`. It
  carried 1857 of them, 21MB of other people's dependencies, in 0.1.3 and 0.1.4,
  the only two releases so far to publish an sdist at all. hatchling's discovery
  honours the repo root `.gitignore` but not the nested one that ignores them.
  The wheel was never affected, which is why it went unnoticed: pip prefers the
  wheel and only a source install ever unpacks the sdist. Now 578KB, with the
  web sources still present so the UI can be rebuilt from it.

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
