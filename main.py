# finkrit/main.py
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from finkritq.asset import Stock
from finkritq.anal.returns import calculate_returns
from finkritq.anal.risk import (
    beta_from_returns,
    component_contribution_to_risk,
    marginal_contribution_to_risk,
    portfolio_conditional_value_at_risk,
    portfolio_downside_deviation,
    portfolio_semivariance,
    portfolio_value_at_risk,
    portfolio_variance,
    portfolio_volatility,
    variance,
    volatility,
)
from finkritq.anal.risk.correlation import correlation_matrix
from finkritq.anal.risk.covariance import covariance_matrix
from finkritq.anal.risk.drawdown import (
    portfolio_drawdown,
    portfolio_maximum_drawdown,
)
from finkritq.data.providers import YFinanceProvider
from finkritq.data.registry import DataRegistry
from finkritq.datatype import (
    AccountRegistrationType,
    Currency,
    CustodianType,
    Exchange,
    MarketIndex,
    VaREstimationMethod,
)
from finkritq.portfolio import Account, Lot, Portfolio, PortfolioData, Position
from finkritq.portfolio.custodian import Custodian


def _make_position(
    stock: Stock,
    account: Account,
    position_id: str,
    lot_id: str,
    quantity: Decimal,
    cost: Decimal,
    acquired: date,
) -> Position:
    lot = Lot(id=lot_id, quantity=quantity, cost_per_share=cost, acquired=acquired)
    return Position(id=position_id, asset=stock, lots=(lot,))


def main():

    registry = DataRegistry()
    yahoo = YFinanceProvider()
    registry.register_history(yahoo)
    registry.register_snapshot(yahoo)

    # -----------------------------------------------------------------------
    # Assets
    # -----------------------------------------------------------------------

    apple     = Stock("AAPL", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Apple Inc.")
    microsoft = Stock("MSFT", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Microsoft Corporation")
    tesla     = Stock("TSLA", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Tesla, Inc.")
    amazon    = Stock("AMZN", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Amazon.com, Inc.")
    nvidia    = Stock("NVDA", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="NVIDIA Corporation")
    alphabet  = Stock("GOOGL", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Alphabet Inc.")
    meta      = Stock("META", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Meta Platforms, Inc.")
    netflix   = Stock("NFLX", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Netflix, Inc.")
    broadcom  = Stock("AVGO", currency=Currency.USD, exchange=Exchange.NASDAQ, company_name="Broadcom Inc.")
    jp_morgan = Stock("JPM",  currency=Currency.USD, exchange=Exchange.NYSE,   company_name="JPMorgan Chase & Co.")

    # -----------------------------------------------------------------------
    # Portfolio construction
    # -----------------------------------------------------------------------

    custodian = Custodian(type=CustodianType.SCHWAB)
    account = Account(
        id="acct-1",
        account_number="123456789",
        name="Main Brokerage",
        custodian=custodian,
        account_registration_type=AccountRegistrationType.INDIVIDUAL,
    )

    holdings = [
        (apple,     "pos-aapl",  "lot-aapl",  Decimal("15"), Decimal("185.50"),  date(2024, 1, 15)),
        (microsoft, "pos-msft",  "lot-msft",  Decimal("8"),  Decimal("420.10"),  date(2024, 2, 12)),
        (tesla,     "pos-tsla",  "lot-tsla",  Decimal("5"),  Decimal("240.75"),  date(2024, 3,  5)),
        (amazon,    "pos-amzn",  "lot-amzn",  Decimal("12"), Decimal("175.30"),  date(2024, 2, 20)),
        (nvidia,    "pos-nvda",  "lot-nvda",  Decimal("6"),  Decimal("950.00"),  date(2024, 4,  8)),
        (alphabet,  "pos-googl", "lot-googl", Decimal("10"), Decimal("165.80"),  date(2024, 1, 30)),
        (meta,      "pos-meta",  "lot-meta",  Decimal("4"),  Decimal("510.20"),  date(2024, 5, 15)),
        (netflix,   "pos-nflx",  "lot-nflx",  Decimal("3"),  Decimal("640.50"),  date(2024, 6, 10)),
        (broadcom,  "pos-avgo",  "lot-avgo",  Decimal("2"),  Decimal("1450.00"), date(2024, 7,  1)),
        (jp_morgan, "pos-jpm",   "lot-jpm",   Decimal("10"), Decimal("198.40"),  date(2024, 3, 18)),
    ]

    for stock, pos_id, lot_id, qty, cost, acquired in holdings:
        pos = _make_position(stock, account, pos_id, lot_id, qty, cost, acquired)
        account.add_position(pos)

    portfolio = Portfolio(id="port-1", name="Tech Portfolio", accounts=[account])

    # -----------------------------------------------------------------------
    # Snapshots (update last_price on each position)
    # -----------------------------------------------------------------------

    with ThreadPoolExecutor() as executor:
        snapshots = list(executor.map(registry.snapshot, portfolio.assets))

    asset_snapshot_map = dict(zip(portfolio.assets, snapshots))

    for pos in account.positions:
        snap = asset_snapshot_map[pos.asset]
        pos.last_price = Decimal(str(snap.last_price))

    print("Portfolio Snapshot")
    print("-" * 90)
    print(f"{'Ticker':<8}{'Qty':>8}{'Avg Cost':>12}{'Last':>12}{'Value':>15}")
    print("-" * 90)

    total_value = Decimal("0")
    total_cost  = Decimal("0")
    total_daily_pnl = Decimal("0")

    for pos in account.positions:
        snap = asset_snapshot_map[pos.asset]
        mv   = pos.market_value
        prev = Decimal(str(snap.previous_close))
        daily_pnl = (pos.last_price - prev) * pos.quantity
        total_value    += mv
        total_cost     += pos.cost_basis
        total_daily_pnl += daily_pnl
        print(
            f"{pos.asset.ticker:<8}"
            f"{float(pos.quantity):>8.2f}"
            f"{float(pos.average_cost):>12.2f}"
            f"{float(pos.last_price):>12.2f}"
            f"{float(mv):>15.2f}"
        )

    print("-" * 90)
    print(f"Portfolio Value : ${float(total_value):,.2f}")
    print(f"Cost Basis      : ${float(total_cost):,.2f}")
    print(f"Unrealized P&L  : ${float(total_value - total_cost):,.2f}")
    print(f"Daily P&L       : ${float(total_daily_pnl):,.2f}")

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    portfolio_data = PortfolioData.from_registry(portfolio, registry)

    benchmark = registry.history(MarketIndex.SP500.as_asset())

    print("\nStock Betas (vs S&P 500)")
    print("-" * 70)
    print(f"{'Ticker':<8}{'Beta':>10}{'Volatility':>15}{'Variance':>15}")
    print("-" * 70)

    for asset in portfolio.assets:
        asset_history = portfolio_data.asset_history(asset)
        asset_history, benchmark_history = asset_history.align(benchmark)
        asset_returns    = calculate_returns(asset_history.close)
        benchmark_returns = calculate_returns(benchmark_history.close)
        asset_beta      = beta_from_returns(asset_returns, benchmark_returns)
        asset_variance  = variance(asset_history)
        asset_volatility = volatility(asset_history)
        print(
            f"{asset.ticker:<8}"
            f"{asset_beta:>10.3f}"
            f"{asset_variance:>15.4f}"
            f"{asset_volatility:>15.2%}"
        )

    print("\nCovariance Matrix")
    print("-" * 80)
    cov = covariance_matrix(portfolio_data)
    print(f"{'':<8}", end="")
    for asset in portfolio_data.assets:
        print(f"{asset.ticker:>10}", end="")
    print()
    for asset, row in zip(portfolio_data.assets, cov):
        print(f"{asset.ticker:<8}", end="")
        for value in row:
            print(f"{value:>10.5f}", end="")
        print()

    print("\nCorrelation Matrix")
    print("-" * (10 + 10 * portfolio_data.n_assets))
    corr = correlation_matrix(portfolio_data)
    print(f"{'':<8}", end="")
    for asset in portfolio_data.assets:
        print(f"{asset.ticker:>10}", end="")
    print()
    for asset, row in zip(portfolio_data.assets, corr):
        print(f"{asset.ticker:<8}", end="")
        for value in row:
            print(f"{value:>10.3f}", end="")
        print()

    print("\nPortfolio Risk")
    print("-" * 40)
    print(f"Portfolio Variance   : {portfolio_variance(portfolio_data):.6f}")
    print(f"Portfolio Volatility : {portfolio_volatility(portfolio_data):.2%}")

    print("\nPortfolio Drawdown")
    print("-" * 40)
    drawdown     = portfolio_drawdown(portfolio_data)
    max_drawdown = portfolio_maximum_drawdown(portfolio_data)
    print(f"Maximum Drawdown : {max_drawdown:.2%}")
    print(f"\n{'Date':<12}{'Drawdown':>15}")
    print("-" * 30)
    for dt, dd in zip(portfolio_data.dates, drawdown):
        print(f"{str(dt)[:10]:<12} {dd:>15.2%}")

    print(f"Semi-Variance      : {portfolio_semivariance(portfolio_data):.6f}")
    print(f"Downside Deviation : {portfolio_downside_deviation(portfolio_data):.2%}")

    print("\nPortfolio Value at Risk")
    print("-" * 40)
    print(f"Historical VaR : {portfolio_value_at_risk(portfolio_data, method=VaREstimationMethod.HISTORICAL):.2%}")
    print(f"Parametric VaR : {portfolio_value_at_risk(portfolio_data, method=VaREstimationMethod.PARAMETRIC):.2%}")
    print(f"Monte Carlo VaR: {portfolio_value_at_risk(portfolio_data, method=VaREstimationMethod.MONTE_CARLO):.2%}")

    print("\nPortfolio Conditional Value at Risk")
    print("-" * 40)
    for method, label in [
        (VaREstimationMethod.HISTORICAL,  "Historical"),
        (VaREstimationMethod.PARAMETRIC,  "Parametric"),
        (VaREstimationMethod.MONTE_CARLO, "Monte Carlo"),
    ]:
        cvar = portfolio_conditional_value_at_risk(portfolio_data, method=method)
        print(f"{label} CVaR : {cvar:.2%} (${cvar * float(total_value):,.2f})")

    print("\nPortfolio Risk Contributions")
    print("-" * 60)
    mctr = marginal_contribution_to_risk(portfolio_data)
    cctr = component_contribution_to_risk(portfolio_data)
    print(f"{'Ticker':<10}{'Weight':>12}{'MCTR':>15}{'CCTR':>15}")
    print("-" * 60)
    for asset, weight, marginal, component in zip(portfolio_data.assets, portfolio_data.weight_vector, mctr, cctr):
        print(f"{asset.ticker:<10}{weight:>12.2%}{marginal:>15.4%}{component:>15.4%}")
    print("-" * 60)
    print(f"{'Portfolio Volatility':<22}{portfolio_volatility(portfolio_data):>15.4%}")
    print(f"{'Sum of CCTR':<22}{cctr.sum():>15.4%}")


if __name__ == "__main__":
    main()

