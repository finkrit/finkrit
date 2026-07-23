<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/finkrit-logo-horizontal-dark.png">
    <img alt="finkrit" src="assets/finkrit-logo-horizontal-light.png" width="260">
  </picture>
</p>

Portfolio risk, performance, optimization, and tax analytics. An open core
quant engine, with an optional conversational agent layer and a web dashboard
on top.

## What is in here

finkrit is a small, layered stack, a quant core with Agentic AI, an API, and a web app built on top.

| Path | Import name | What it does |
| - | - | - |
| `packages/finkritq` | `finkritq` | Deterministic quant core. Holdings, tax lots, prices, risk, performance, optimization, and tax. No agent or web dependency. |
| `packages/finkritintel` | `finkritintel` | Tool contracts and capabilities. The bridge that exposes the core as callable tools. |
| `packages/finagent` | `finagent` | Conversational agents over the capabilities, built on pydantic-ai. |
| `services/api/finkritserver` | `finkritserver` | FastAPI layer that serves the JSON API and the built web app. |
| `apps/finkritweb` | (web) | SvelteKit dashboard. Upload a portfolio, see it, ask about it. |

`finkritq` is the open core and stands on its own. Everything above it adds
tools and an agent, and stays optional.

## Quickstart

```bash
pip install finkrit           # or: pipx install finkrit
export LLM_API_KEY=sk-...      # any OpenAI, Anthropic, or Google key
finkrit                        # start the dashboard, opens your browser
```

finkrit needs an LLM key. Getting a portfolio in means uploading a CSV, which
the model parses, so it does not start without one. Any provider pydantic-ai
supports works, keyed by the single LLM_API_KEY variable, or pass it inline with
`finkrit --key sk-...`.

Prefer the terminal? `finkrit cli` chats with the agent over a portfolio instead.

## Command line

```
finkrit            start the dashboard (opens your browser)
finkrit web        the same, explicit
finkrit cli        chat with the agent in the terminal
```

The dashboard takes:

```
finkrit --key sk-...           the LLM key inline (should match provider)
finkrit --model openai:gpt-5   pick the provider and model (defaults to openai:gpt-5)
finkrit --port 8001            serve on a different port
finkrit --dev                  Vite hot reload (source checkout only in case you want to tinker)
```

### Chat with the agent

`finkrit cli` is a REPL over a portfolio. With no `--file` it uses a seeded
offline portfolio, 40 AAPL, 30 MSFT, 20 NVDA, 25 JPM, and 35 XOM, each at a cost
basis of 100 acquired 2022-01-03, priced with deterministic fake data so runs
are reproducible. Point it at your own holdings with a CSV instead, which
switches to live market data:

```bash
finkrit cli --file my_holdings.csv
```

A CSV file has one row per holding, with four columns: ticker, quantity, cost
per share, and acquired date. For example:

| ticker | quantity | cost_per_share | acquired |
| - | - | - | - |
| AAPL | 180 | 142.35 | 2021-05-12 |
| MSFT | 95 | 238.60 | 2021-02-18 |
| NVDA | 140 | 168.20 | 2023-03-09 |

Column names are matched case-insensitively against common aliases, so a
typical brokerage export loads without renaming anything:

| Field | Recognized column names |
| - | - |
| Ticker | `ticker`, `symbol` |
| Quantity | `quantity`, `shares`, `qty`, `units` |
| Cost per share | `cost_per_share`, `cost basis / share`, `cost basis`, `avg cost`, `cost`, `price`, `price paid` |
| Acquired | `acquired`, `date acquired`, `purchase date`, `date` |

Dates accept `YYYY-MM-DD`, `MM/DD/YYYY`, `MM/DD/YY`, or `DD-MM-YYYY`. Commas in
numbers are stripped, extra columns are ignored, and a missing or unreadable
date falls back to a default.

That strict parser is the `finkrit cli --file` path. The **web upload** is
looser: the raw file goes to the model, which maps whatever columns and formats
it finds onto the same four fields and flags anything it had to guess for you to
review, so almost any layout works there.

```
-f, --file PATH    load a portfolio CSV, uses live prices
--ai openai        provider shortcut or a full provider:name string
-ag 0|1|2|3        router, risk, optimization, performance
--key sk-...       the LLM key
--quiet            hide the live tool-call trace
```

## From source

To hack on finkrit, clone it and use the bootstrap, which sets up a virtual
environment, installs dependencies, builds the web app, and launches.

```bash
git clone https://github.com/finkrit/finkrit
cd finkrit
export LLM_API_KEY=sk-...
./run                          # same flags as finkrit web, for example --dev
```

Prerequisites: Python 3.11 or newer and Node 18 or newer. Later runs skip the
setup.

## Using the quant core on its own

`finkritq` is the open core, published on its own so you can install just the
quant engine without the agent or web layers.

```bash
pip install finkritq            # core, numpy and scipy only
pip install "finkritq[data]"    # adds the live yfinance data provider
```

It also ships a runnable demo that prints every analytic pillar over a
portfolio, no agent involved:

```bash
python -m finkritq                                             # seeded, offline
python -m finkritq real NVDA KO PG --benchmark SPY --years 3   # needs [data]
```

## Development

Sources live under `packages/` and `services/api/`. The test runner is
configured to put those on the import path, so a fresh clone runs the suite
with no extra setup.

```bash
pip install -r requirements.txt
pytest                       # the whole suite
pytest packages/finkritq     # one package
```

## Status

Early and moving. The layers above `finkritq` are the newest. Expect the
agent and web surfaces to change while the core settles.

## Disclaimer

finkrit is for educational and informational purposes only. It is not financial,
investment, or tax advice, and nothing it produces is a recommendation to buy or
sell any security. Use your own judgment and consult a licensed professional
before making decisions.

The optional data provider uses [yfinance](https://github.com/ranaroussi/yfinance)
to pull market data from Yahoo Finance. finkrit and yfinance are not affiliated
with, endorsed by, or sponsored by Yahoo. That data is subject to Yahoo's terms
of use and is intended for personal and educational use. Verify anything you rely
on against an authoritative source.

The software is provided as is, without warranty of any kind.

## License

Apache-2.0. See [LICENSE](LICENSE).
