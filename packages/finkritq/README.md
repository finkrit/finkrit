# finkritq

Deterministic portfolio quant core: risk, performance, optimization, and tax
analytics over holdings you supply. Pure numpy and scipy, no agent or web
dependency. This is the open core of the [finkrit](https://github.com/finkrit/finkrit)
stack, published on its own for use as a standalone library.

## Install

```bash
pip install finkritq              # core: numpy + scipy
pip install "finkritq[data]"      # adds the live yfinance market data provider
```

## What it does

- **Risk**: volatility, variance, semivariance, downside deviation, drawdown
  and maximum drawdown, value at risk and conditional value at risk, beta,
  marginal and component contribution to risk, forward return range.
- **Performance**: total and annualized return, Sharpe, Sortino, Calmar,
  information ratio, Jensen's alpha, contribution to return, net of fees,
  time and money weighted return, Brinson attribution.
- **Optimization**: mean variance weights (minimum variance, maximum Sharpe,
  target return), long only and box constrained, Ledoit-Wolf shrinkage,
  rebalancing to a target or a policy.
- **Tax**: tax lots, tax-loss harvest candidates, tax-aware rebalancing.

## Quickstart

```python
from datetime import date
from decimal import Decimal

from finkritq.asset import Stock
from finkritq.datatype import Currency, Exchange
from finkritq.portfolio import Portfolio, Position, TaxLot
from finkritq.anal.risk import portfolio_volatility

stock = Stock(ticker="AAPL", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Apple Inc")
lot = TaxLot(id="lot-1", quantity=Decimal("100"), cost_per_share=Decimal("150"), acquired=date(2022, 1, 3))
portfolio = Portfolio(id="p1", name="Demo", positions=[Position(id="pos-1", asset=stock, lots=(lot,))])
```

Feed it your own price history, or install the `data` extra to pull live daily
closes through the bundled provider.

## Runnable demo

```bash
python -m finkritq              # seeded, offline synthetic market
python -m finkritq real NVDA KO PG --benchmark SPY --years 3    # needs [data]
```

## License

Apache-2.0. See [LICENSE](LICENSE).
