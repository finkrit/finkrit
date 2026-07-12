# finkrit/main.py
from concurrent.futures import ThreadPoolExecutor

from datetime import date
from packages.finq.asset import Stock, Lot
from packages.finq.anal.returns import calculate_returns
from packages.finq.anal.risk import (
    beta_from_returns, 
    portfolio_conditional_value_at_risk, 
    portfolio_downside_deviation, 
    portfolio_semivariance, 
    variance, 
    volatility)
from packages.finq.anal.risk.correlation import correlation_matrix
from packages.finq.data.providers import YFinanceProvider
from packages.finq.data.registry import DataRegistry
from packages.finq.datatype import Currency, Exchange, MarketIndex, VaREstimationMethod
from packages.finq.portfolio import Portfolio, Position, PortfolioSnapshot
from packages.finq.anal.risk.covariance import covariance_matrix
from packages.finq.anal.risk.drawdown import (
    portfolio_drawdown,
    portfolio_maximum_drawdown,
)
from packages.finq.anal.risk.valueatrisk import portfolio_value_at_risk
from packages.finq.anal.risk.variance import portfolio_variance
from packages.finq.anal.risk.volatility import portfolio_volatility




def main():

    registry = DataRegistry()

    yahoo = YFinanceProvider()
    registry.register_history(yahoo)
    registry.register_snapshot(yahoo)

    apple = Stock(
        "AAPL",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Apple Inc.",
    )

    microsoft = Stock(
        "MSFT",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Microsoft Corporation",
    )

    tesla = Stock(
        "TSLA",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Tesla, Inc.",
    )

    amazon = Stock(
        "AMZN",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Amazon.com, Inc.",
    )

    nvidia = Stock(
        "NVDA",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="NVIDIA Corporation",
    )

    alphabet = Stock(
        "GOOGL",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Alphabet Inc.",
    )

    meta = Stock(
        "META",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Meta Platforms, Inc.",
    )

    netflix = Stock(
        "NFLX",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Netflix, Inc.",
    )

    broadcom = Stock(
        "AVGO",
        currency=Currency.USD,
        exchange=Exchange.NASDAQ,
        company_name="Broadcom Inc.",
    )

    jp_morgan = Stock(
        "JPM",
        currency=Currency.USD,
        exchange=Exchange.NYSE,
        company_name="JPMorgan Chase & Co.",
    )

    portfolio = Portfolio([
        Position(asset=apple, lots=(Lot(asset=apple, quantity=15, cost_per_share=185.50, acquired=date(2024, 1, 15)),)),
        Position(asset=microsoft, lots=(Lot(asset=microsoft, quantity=8, cost_per_share=420.10, acquired=date(2024, 2, 12)),)),
        Position(asset=tesla, lots=(Lot(asset=tesla, quantity=5, cost_per_share=240.75, acquired=date(2024, 3, 5)),)),
        Position(asset=amazon, lots=(Lot(asset=amazon, quantity=12, cost_per_share=175.30, acquired=date(2024, 2, 20)),)),
        Position(asset=nvidia, lots=(Lot(asset=nvidia, quantity=6, cost_per_share=950.00, acquired=date(2024, 4, 8)),)),
        Position(asset=alphabet, lots=(Lot(asset=alphabet, quantity=10, cost_per_share=165.80, acquired=date(2024, 1, 30)),)),
        Position(asset=meta, lots=(Lot(asset=meta, quantity=4, cost_per_share=510.20, acquired=date(2024, 5, 15)),)),
        Position(asset=netflix, lots=(Lot(asset=netflix, quantity=3, cost_per_share=640.50, acquired=date(2024, 6, 10)),)),
        Position(asset=broadcom, lots=(Lot(asset=broadcom, quantity=2, cost_per_share=1450.00, acquired=date(2024, 7, 1)),)),
        Position(asset=jp_morgan, lots=(Lot(asset=jp_morgan, quantity=10, cost_per_share=198.40, acquired=date(2024, 3, 18)),)),
    ])

    with ThreadPoolExecutor() as executor:
        snapshots = list(executor.map(registry.snapshot, portfolio.assets))

    asset_snapshots = dict(zip(portfolio.assets, snapshots))

    snapshot = PortfolioSnapshot(
        portfolio=portfolio,
        _snapshots=asset_snapshots,
    )
    
    print("Portfolio Snapshot")
    print("-" * 90)

    print(
        f"{'Ticker':<8}"
        f"{'Qty':>8}"
        f"{'Avg Cost':>12}"
        f"{'Last':>12}"
        f"{'Value':>15}"
    )

    print("-" * 90)

    for position in portfolio.positions:
        asset_snapshot = snapshot[position.asset]
        market_value = position.market_value(asset_snapshot.last_price)
        print(
            f"{position.asset.ticker:<8}"
            f"{position.quantity:>8.2f}"
            f"{position.average_cost:>12.2f}"
            f"{asset_snapshot.last_price:>12.2f}"
            f"{market_value:>15.2f}"
        )

    print("-" * 90)
    print(f"Portfolio Value : ${snapshot.market_value:,.2f}")
    print(f"Cost Basis      : ${snapshot.cost_basis:,.2f}")

    if snapshot.unrealized_pnl is not None:
        print(f"Unrealized P&L  : ${snapshot.unrealized_pnl:,.2f}")

    print(f"Daily P&L       : ${snapshot.daily_pnl:,.2f}")

    portfolio_data = registry.history(portfolio)

    benchmark = registry.history(
        MarketIndex.SP500.as_asset(),
    )

    print("\nStock Betas (vs S&P 500)")
    print("-" * 70)
    print(f"{'Ticker':<8}{'Beta':>10}{'Volatility':>15}{'Variance':>15}")
    print("-" * 70)
    

    for asset in portfolio.assets:
        asset_history = portfolio_data.asset_history(asset)
        asset_history, benchmark_history = asset_history.align(benchmark)
        asset_returns = calculate_returns(asset_history.close)
        benchmark_returns = calculate_returns(benchmark_history.close)
        
        asset_beta = beta_from_returns(asset_returns, benchmark_returns)
        asset_variance = variance(asset_history)
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

    portfolio_var = portfolio_variance(portfolio_data)
    portfolio_vol = portfolio_volatility(portfolio_data)

    print(f"Portfolio Variance   : {portfolio_var:.6f}")
    print(f"Portfolio Volatility : {portfolio_vol:.2%}")

    print("\nPortfolio Drawdown")
    print("-" * 40)

    drawdown = portfolio_drawdown(portfolio_data)
    max_drawdown = portfolio_maximum_drawdown(portfolio_data)

    print(f"Maximum Drawdown : {max_drawdown:.2%}")
    print()

    print(f"{'Date':<12}{'Drawdown':>15}")
    print("-" * 30)

    for dt, dd in zip(portfolio_data.dates, drawdown):
        print(f"{str(dt)[:10]:<12} {dd:>15.2%}")

    portfolio_semivar = portfolio_semivariance(portfolio_data)
    portfolio_downside_dev = portfolio_downside_deviation(portfolio_data)

    print(f"Semi-Variance      : {portfolio_semivar:.6f}")
    print(f"Downside Deviation : {portfolio_downside_dev:.2%}")

    print("\nPortfolio Value at Risk")
    print("-" * 40)

    historical_var = portfolio_value_at_risk(
        portfolio_data,
        method=VaREstimationMethod.HISTORICAL,
    )

    parametric_var = portfolio_value_at_risk(
        portfolio_data,
        method=VaREstimationMethod.PARAMETRIC,
    )

    monte_carlo_var = portfolio_value_at_risk(
        portfolio_data,
        method=VaREstimationMethod.MONTE_CARLO,
    )

    print(f"Historical VaR : {historical_var:.2%}")
    print(f"Parametric VaR : {parametric_var:.2%}")
    print(f"Monte Carlo VaR: {monte_carlo_var:.2%}")

    print("\nPortfolio Conditional Value at Risk")
    print("-" * 40)

    historical_cvar = portfolio_conditional_value_at_risk(portfolio_data, method=VaREstimationMethod.HISTORICAL)
    parametric_cvar = portfolio_conditional_value_at_risk(portfolio_data, method=VaREstimationMethod.PARAMETRIC)
    monte_carlo_cvar = portfolio_conditional_value_at_risk(portfolio_data, method=VaREstimationMethod.MONTE_CARLO,)
    historical_cvar_value = historical_cvar * snapshot.market_value
    parametric_cvar_value = parametric_cvar * snapshot.market_value
    monte_carlo_cvar_value = monte_carlo_cvar * snapshot.market_value

    print(
        f"Historical CVaR : {historical_cvar:.2%} "
        f"(${historical_cvar_value:,.2f})"
    )

    print(
        f"Parametric CVaR : {parametric_cvar:.2%} "
        f"(${parametric_cvar_value:,.2f})"
    )

    print(
        f"Monte Carlo CVaR: {monte_carlo_cvar:.2%} "
        f"(${monte_carlo_cvar_value:,.2f})"
    )

if __name__ == "__main__":
    main()
    
