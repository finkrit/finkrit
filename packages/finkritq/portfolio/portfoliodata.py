# finkrit/packages/finkritq/portfolio/portfoliodata.py
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from finkritq.transform.returns import periodic_returns
from finkritq.asset import Asset
from finkritq.datatype import PriceHistory, ReturnCalculationMethod
from finkritq.portfolio import Portfolio

if TYPE_CHECKING:
    from finkritq.data.registry import DataRegistry
    from finkritq.portfolio import Position


@dataclass(frozen=True, slots=True)
class PortfolioData:
    """
    Market data for a portfolio.

    Stores aligned price histories for each holding and exposes
    derived portfolio-level series and analytics.
    """

    portfolio: Portfolio
    _histories: dict[Asset, PriceHistory]

    @classmethod
    def from_registry(
        cls,
        portfolio: Portfolio,
        registry: DataRegistry,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        max_workers: int | None = None,
    ) -> "PortfolioData":

        if len(portfolio.positions) == 0:
            raise ValueError("Portfolio contains no positions.")

        def fetch(position):
            return (
                position.asset,
                registry.history(
                    position.asset,
                    start=start,
                    end=end,
                    interval=interval,
                ),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(fetch, portfolio.positions))

        assets = [asset for asset, _ in results]
        histories = [history for _, history in results]
        histories = PriceHistory.align_many(histories)
        return cls(portfolio=portfolio, _histories=dict(zip(assets, histories)))

    def __post_init__(self):

        if not self._histories:
            raise ValueError("PortfolioData requires at least one history.")

        missing = [p.asset for p in self.portfolio.positions if p.asset not in self._histories]
        if missing:
            raise ValueError("Missing histories for: , ".join(asset.ticker for asset in missing))

        first = next(iter(self._histories.values()))
        for asset, history in self._histories.items():

            if len(history) != len(first):
                raise ValueError(f"{asset.ticker} history has different length.")

            if not np.array_equal(history.dates, first.dates):
                raise ValueError(f"{asset.ticker} history is not aligned.")

    def __getitem__(self, asset: Asset) -> PriceHistory:
        return self._histories[asset]

    @property
    def assets(self) -> tuple[Asset, ...]:
        return tuple(self._histories)

    @property
    def dates(self) -> NDArray[np.datetime64]:
        return next(iter(self._histories.values())).dates

    @staticmethod
    def _quantity(position: "Position") -> float:
        # The single Decimal->float boundary for holdings. The domain model keeps
        # share counts as exact Decimals, the analytics work in float, so every
        # quantity crosses to float here and nowhere else, keeping the conversion
        # in one greppable place.
        return float(position.quantity)

    @property
    def value(self) -> NDArray[np.float64]:
        """
        Portfolio market value over the lookback window.

        Convention: *current* holdings are applied across the whole history,
        i.e. today's quantities times each day's close. TaxLot `acquired` dates
        are intentionally ignored, this is the standard "current-composition" basis
        for risk analytics (what is today's portfolio's risk, given how these
        assets have historically behaved?), NOT a position-aware backtest of
        what you actually held on each past date.
        """
        values = np.zeros(len(self), dtype=np.float64)
        for position in self.portfolio.positions:
            values += (self[position.asset].close * self._quantity(position))

        return values
    
    @property
    def histories(self) -> tuple[PriceHistory, ...]:
        return tuple(self._histories.values())
    
    @property
    def n_assets(self) -> int:
        return len(self._histories)
    
    @property
    def price_matrix(self) -> NDArray[np.float64]:
        """
        Matrix of closing prices.

        Shape
        -----
        (n_assets, n_periods)
        """
        return np.asarray([
            history.close
            for history in self.histories
        ])
    
    @property
    def n_periods(self) -> int:
        return len(self)

    @property
    def weights(self) -> dict[Asset, float]:

        # Accumulate market value per asset: the same asset can appear in
        # more than one position, so we sum rather than overwrite.
        # (A dict comprehension keyed by asset would silently drop all but the
        # last position of a repeated asset, and disagree with .value, which
        # already sums across positions.)
        values: dict[Asset, float] = {}
        for position in self.portfolio.positions:
            market_value = self.latest_prices[position.asset] * self._quantity(position)
            values[position.asset] = values.get(position.asset, 0.0) + market_value

        total = sum(values.values())
        return {
            asset: value / total
            for asset, value in values.items()
        }

    @property
    def start_weights(self) -> dict[Asset, float]:
        # Market-value weights at the START of the window (first close). This is the
        # basis for buy-and-hold contribution-to-return, whose per-asset pieces sum
        # exactly to the portfolio's total return over the window.
        values: dict[Asset, float] = {}
        for position in self.portfolio.positions:
            start_price = self[position.asset].close[0]
            values[position.asset] = values.get(position.asset, 0.0) + start_price * self._quantity(position)

        total = sum(values.values())
        return {
            asset: value / total
            for asset, value in values.items()
        }

    @property
    def weight_vector(self) -> NDArray[np.float64]:
        weights = self.weights
        return np.array([weights[asset] for asset in self.assets], dtype=np.float64)
    
    @property
    def start(self) -> np.datetime64:
        return self.dates[0]

    @property
    def end(self) -> np.datetime64:
        return self.dates[-1]
    
    @property
    def latest_prices(self) -> dict[Asset, float]:
        return {
            asset: history.close[-1]
            for asset, history in self.items()
        }

    def __len__(self):
        return len(self.dates)

    def __repr__(self):
        return (f"PortfolioData({len(self.assets)} assets, {self.start} -> {self.end}, {len(self)} observations)")
    
    def return_matrix(
        self,
        method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    ) -> NDArray[np.float64]:

        return np.vstack([
            periodic_returns(history.close, method)
            for history in self.histories
        ])
    
    # ------------------------------------------------------------------------
    # Portfolio return series with the two WeightingBasis choices.
    #
    # A multi-asset portfolio has no single return series, you first choose what
    # stays constant as prices move (see datatype.WeightingBasis for the full
    # explanation). These two methods are the concrete constructions of that
    # choice, and every portfolio_* risk metric ultimately consumes one of them.
    # ------------------------------------------------------------------------

    def realized_returns(self) -> NDArray[np.float64]:
        """
        Buy-and-hold portfolio return series (WeightingBasis.BUY_AND_HOLD).

        Holds today's SHARE COUNTS fixed and lets weights drift: the SIMPLE
        return of the actual dollar value path, V(t) = Σ q_i·P_i(t). `self.value`
        already applies today's quantities across the whole history, so its period
        returns ARE the buy-and-hold portfolio returns, no weighting step here.

        Portfolio returns are always simple, so there is no `method`: a portfolio
        return is a simple return by nature (see `constant_mix_returns`), so the
        log-vs-simple choice does not exist at the portfolio level. Pick a
        convention on a single asset's series instead (asset-level functions and
        `periodic_returns` still take `method`).
        """

        # self.value is the value path (one number per day), its simple returns
        # are the portfolio returns directly. Nothing per-asset to combine.
        return periodic_returns(self.value, ReturnCalculationMethod.SIMPLE)

    def constant_mix_returns(self) -> NDArray[np.float64]:
        """
        Constant-mix portfolio return series (WeightingBasis.CONSTANT_MIX).

        Holds today's WEIGHTS `w` fixed for every period (a portfolio rebalanced
        back to `w` each period) and takes the weighted sum of the SIMPLE asset
        returns:

            r_p(t) = Σ_i w_i · r_i(t)

        Simple is not a choice here: Σ_i w_i r_i is a valid portfolio return only
        for simple returns (log returns do not sum across assets). By linearity of
        variance, Var(Σ_i w_i r_i) = wᵀΣw exactly, so this series' variance equals
        the quadratic form `portfolio_variance` uses under CONSTANT_MIX, the
        series and matrix forms are two views of the same number.
        """

        # weight_vector is (n_assets,), return_matrix is (n_assets, n_periods).
        # The matmul contracts the asset axis, giving the (n_periods,)
        # weighted-sum return series r_p(t) = Σ_i w_i · r_i(t).
        return self.weight_vector @ self.return_matrix(ReturnCalculationMethod.SIMPLE)

    def portfolio_returns(self) -> NDArray[np.float64]:
        """
        Deprecated alias for `realized_returns`, kept so pre-existing callers
        keep working. New code should call `realized_returns` /
        `constant_mix_returns` explicitly so the basis is visible at the call site.
        """
        return self.realized_returns()

    def aligned_close(self, benchmark: PriceHistory) -> NDArray[np.float64]:
        """
        Benchmark closing prices sampled at THIS portfolio's observation dates.

        Benchmark-relative metrics (beta, tracking error, information ratio,
        alpha) need the benchmark measured on the same periods as the portfolio.
        Rather than assume the two were fetched over identical calendars, we index
        the benchmark by date so its returns line up period-for-period with the
        portfolio's own. Extra benchmark dates are ignored, a benchmark missing
        any portfolio date is an alignment error and raises.
        """
        close_by_date = dict(zip(benchmark.dates.tolist(), benchmark.close))
        try:
            aligned = [close_by_date[day] for day in self.dates.tolist()]
        except KeyError as missing:
            raise ValueError(
                f"Benchmark has no observation for portfolio date {missing.args[0]}."
            ) from None
        return np.asarray(aligned, dtype=np.float64)


    def items(self) -> tuple[tuple[Asset, PriceHistory], ...]:
        return tuple(self._histories.items())

    def asset_returns(
        self,
        asset: Asset,
        method: ReturnCalculationMethod = ReturnCalculationMethod.LOG,
    ) -> NDArray[np.float64]:

        return periodic_returns(self[asset].close, method=method)
    
    def asset_history(self, asset: Asset) -> PriceHistory:
        return self[asset]


