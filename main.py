# finkrit/main.py

from packages.finq.asset import Stock
from packages.finq.data.providers import YFinanceProvider
from packages.finq.data.registry import DataRegistry
from packages.finq.datatype import Currency, Exchange
from packages.finq.portfolio import Portfolio, Position, PortfolioSnapshot


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
        Position(asset=apple, quantity=15, average_cost=185.50),
        Position(asset=microsoft, quantity=8, average_cost=420.10),
        Position(asset=tesla, quantity=5, average_cost=240.75),
        Position(asset=amazon, quantity=12, average_cost=175.30),
        Position(asset=nvidia, quantity=6, average_cost=950.00),
        Position(asset=alphabet, quantity=10, average_cost=165.80),
        Position(asset=meta, quantity=4, average_cost=510.20),
        Position(asset=netflix, quantity=3, average_cost=640.50),
        Position(asset=broadcom, quantity=2, average_cost=1450.00),
        Position(asset=jp_morgan, quantity=10, average_cost=198.40),
    ])

    asset_snapshots = {
        asset: registry.snapshot(asset)
        for asset in portfolio.assets
    }

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

        market_value = position.quantity * asset_snapshot.last_price

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


if __name__ == "__main__":
    main()