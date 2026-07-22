# finkrit

Portfolio risk, performance, optimization, and tax analytics. An open core
quant engine, with an optional conversational agent layer and a web dashboard
on top.

## What is in here

finkrit is a small layered monorepo.

| Path | Import name | What it does |
| - | - | - |
| `packages/finkritq` | `finkritq` | Deterministic quant core. Holdings, tax lots, prices, risk, performance, optimization, and tax. No agent or web dependency. |
| `packages/finkritintel` | `finkritintel` | Tool contracts and capabilities. The bridge that exposes the core as callable tools. |
| `packages/finagent` | `finagent` | Conversational agents over the capabilities, built on pydantic-ai. |
| `services/api/finkritserver` | `finkritserver` | FastAPI layer that serves the JSON API and the built web app. |
| `apps/finkritweb` | (web) | SvelteKit dashboard. Upload a portfolio, see it, ask about it. |

`finkritq` is the open core and stands on its own. Everything above it adds
tools and an agent, and stays optional.

## Quickstart: the web app

One command runs the dashboard and the API together.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd apps/finkritweb && npm install && cd ../..

export LLM_API_KEY=sk-...        # any OpenAI, Anthropic, or Google key
python scripts/run.py --dev      # Vite hot reload alongside the API
```

Open http://localhost:5173, upload a portfolio CSV, and explore it. The
dashboard and the risk report work with no key. Only upload and chat call an
LLM. Drop the `--dev` flag to build the app once and serve it from FastAPI on
a single origin instead.

Pass `--model` to pick the provider, for example `python scripts/run.py --model openai:gpt-5`.
Any provider pydantic-ai supports works, keyed by the one `LLM_API_KEY`
variable.

## Using the quant core on its own

`finkritq` has no agent or web dependency. A PyPI release is planned. Until
then, put the sources on your path and import it directly.

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

## License

To be decided.
