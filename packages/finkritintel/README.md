# finkritintel

The bridge layer of the [finkrit](https://github.com/finkrit/finkrit) stack.
It exposes [finkritq](https://pypi.org/project/finkritq/) (the deterministic
quant core) as framework-neutral **tool contracts** an agent can call, without
depending on any particular LLM framework.

Deliberately pydantic-free and agent-framework agnostic, so you can wire these
tools into pydantic-ai, LangChain, an MCP server, or your own runtime. finkrit's
own agent layer (finagent) is just one consumer.

## Install

```bash
pip install finkritintel      # pulls finkritq
```

## What it gives you

- **ToolContract** — agent-facing metadata for a tool (name, description, tags),
  independent of how it is implemented.
- **ToolBinding** — a contract paired with an input and output schema and a
  concrete finkritq implementation. `binding.execute(...)` runs it.
- **Capability** — a named group of bindings (risk, performance, optimization)
  an agent exposes as one unit.

The `integration.finkritq` subpackage wires finkritq functions into ready-made
bindings, with room for other data sources later.

## Example

List the tools a capability offers, framework and LLM free:

```python
from finkritintel.capability.risk import RISK_CAPABILITY

for binding in RISK_CAPABILITY.tools:
    print(binding.contract.name, "-", binding.contract.description)
```

Each binding carries the schema and the callable, so a framework author can turn
it into a tool however that framework expects.

## License

Apache-2.0. See [LICENSE](LICENSE).
