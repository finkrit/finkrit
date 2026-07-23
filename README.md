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
git clone https://github.com/finkrit/finkrit
cd finkrit
export LLM_API_KEY=sk-...     # any OpenAI, Anthropic, or Google key
./run
```

finkrit needs an LLM key to run. Getting a portfolio in means uploading a CSV,
which the model parses, so the app does not start without one. Any provider
pydantic-ai supports works, keyed by the single LLM_API_KEY variable. You can
also pass it inline with `./run --key sk-...`.

On the first run the script creates a virtual environment, installs the Python
and web dependencies, builds the web app, starts the server, and opens your
browser. Later runs skip the setup and start right away. Then upload a portfolio
CSV and explore it.

Flags pass straight through to the server:

```bash
./run --dev                   # Vite hot reload, for working on the frontend
./run --key sk-...            # provide the LLM key inline
./run --model openai:gpt-5    # pick the provider and model
./run --port 8001             # serve on a different port
./run --no-browser            # do not open a browser
```

Prerequisites: Python 3.11 or newer and Node 18 or newer. The script installs
everything else.

## Command line

Two terminal entry points beyond the web app. Both read the sources from
`packages/`, so run them with that on the path.

### Chat with the agent

A REPL over a portfolio. By default it uses a seeded offline portfolio.

```bash
PYTHONPATH=packages python -m finagent --key sk-...
```

Point it at your own holdings with a CSV, which switches to live market data:

```bash
PYTHONPATH=packages python -m finagent --key sk-... --file my_holdings.csv
```

The CSV needs a ticker, quantity, cost per share, and acquired date. Common
column names (Symbol, Shares, Avg Cost, Purchase Date, and similar) are
recognized, so a typical brokerage export loads as is.

```
--ai claude|openai|gemini|groq|mistral   or a full provider:name string
-ag 0|1|2|3                              router, risk, optimization, performance
-f, --file PATH                          load a portfolio CSV, uses live prices
--key sk-...                             the LLM key
--quiet                                  hide the live tool-call trace
```

### Run the quant analytics demo

`finkritq` prints every analytic pillar over a portfolio, no agent involved.

```bash
PYTHONPATH=packages python -m finkritq                 # seeded, offline
PYTHONPATH=packages python -m finkritq real NVDA KO PG --benchmark SPY --years 3
```

Installed from PyPI it is just `python -m finkritq` (real mode needs the
`finkritq[data]` extra).

## Using the quant core on its own

`finkritq` is the open core, published on its own so you can install just the
quant engine without the agent or web layers.

```bash
pip install finkritq            # core, numpy and scipy only
pip install "finkritq[data]"    # adds the live yfinance data provider
```

From a clone instead of PyPI, put the sources on your path:

```bash
PYTHONPATH=packages python -c "from finkritq.asset import Stock; print(Stock)"
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
