# finkrit/packages/finkritq/data/providers/yfinanceprovider.py
"""
Live daily price history and snapshots from Yahoo Finance via yfinance.

yfinance is a best-effort scraper of an undocumented endpoint, so it fails in
mundane, look-alike ways: Yahoo rate-limits, it returns an empty frame for an
unknown or delisted ticker, or it hands back nothing for a window that runs
past the last trading day. All of those reach a caller as the same thing, no
data, which then surfaces three layers up as blank risk numbers with no reason
attached.

So this provider is deliberately loud. Every request logs the ticker and the
exact window. A network or parsing failure is logged with the underlying error
and re-raised with context. An empty result is logged as a warning that names
the likely causes, and raised as an error that names the ticker and the window,
rather than a silent empty history.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from finkritq.asset import Asset, AssetSnapshot
from finkritq.data.interfaces import HistoryProvider, SnapshotProvider
from finkritq.datatype import PriceHistory


class YFinanceProvider(HistoryProvider, SnapshotProvider):

    def history(
        self,
        asset: Asset,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:

        if end is None:
            end = date.today()
        if start is None:
            start = end - timedelta(days=365)

        logger.info(f"yfinance history request: {asset.ticker} {start} to {end} interval={interval}")

        try:
            df = yf.download(
                tickers=asset.ticker,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=True,
                progress=False,
            )
        except Exception as exc:  # noqa: BLE001 - yfinance raises a wide range of errors
            logger.error(f"yfinance download failed for {asset.ticker} ({start} to {end}): {exc!r}")
            raise ValueError(
                f"yfinance download failed for '{asset.ticker}' over {start} to {end}: {exc}"
            ) from exc

        if df is None or df.empty:
            logger.warning(
                f"yfinance returned no rows for {asset.ticker} over {start} to {end} "
                f"(interval={interval}). Likely a rate limit, an unknown or delisted "
                f"ticker, or a window with no trading days (for example an end date "
                f"past the last close)."
            )
            raise ValueError(
                f"No historical data for '{asset.ticker}' over {start} to {end} "
                f"(interval {interval}). yfinance returned an empty result, commonly a "
                f"rate limit, an unknown ticker, or a range with no trading days."
            )

        raw_rows = len(df)
        history = self._to_price_history(df)
        dropped = raw_rows - len(history.dates)
        if dropped:
            logger.warning(
                f"yfinance {asset.ticker}: dropped {dropped} row(s) with a non-finite "
                f"close before analysis, commonly the latest not-yet-settled session. "
                f"A single NaN close otherwise poisons every covariance and volatility."
            )
        if len(history.dates) == 0:
            logger.warning(f"yfinance returned only non-finite rows for {asset.ticker} over {start} to {end}")
            raise ValueError(
                f"No usable historical data for '{asset.ticker}' over {start} to {end} "
                f"(interval {interval}). Every returned row had a non-finite close."
            )
        first = str(history.dates[0])[:10] if len(history.dates) else "n/a"
        last = str(history.dates[-1])[:10] if len(history.dates) else "n/a"
        logger.info(f"yfinance history for {asset.ticker}: {len(history.dates)} rows, {first} to {last}")
        return history

    @staticmethod
    def _to_price_history(df: pd.DataFrame) -> PriceHistory:

        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(-1, axis=1)

        # Keep only rows with a finite close. yfinance routinely appends a row for
        # the most recent, not-yet-settled session with NaN OHLC, and can leave the
        # odd NaN mid-series. Everything downstream (returns, covariance, volatility)
        # turns a single NaN close into NaN for the whole portfolio, so filter here
        # at the data boundary rather than let it propagate as a silent null.
        finite_close = np.isfinite(df["Close"].to_numpy(dtype=np.float64))
        df = df[finite_close]

        return PriceHistory(
            dates=df.index.to_numpy(dtype="datetime64[ns]"),
            open=df["Open"].to_numpy(dtype=np.float64),
            high=df["High"].to_numpy(dtype=np.float64),
            low=df["Low"].to_numpy(dtype=np.float64),
            close=df["Close"].to_numpy(dtype=np.float64),
            volume=df["Volume"].to_numpy(dtype=np.int64),
        )

    def snapshot(self, asset: Asset):
        logger.info(f"yfinance snapshot request: {asset.ticker}")

        try:
            info = yf.Ticker(asset.ticker).fast_info
            snap = AssetSnapshot(
                asset=asset,
                last_price=info.last_price,
                previous_close=info.previous_close,
            )
        except Exception as exc:  # noqa: BLE001 - yfinance raises a wide range of errors
            logger.error(f"yfinance snapshot failed for {asset.ticker}: {exc!r}")
            raise ValueError(f"yfinance snapshot failed for '{asset.ticker}': {exc}") from exc

        logger.info(f"yfinance snapshot for {asset.ticker}: last={snap.last_price} prev={snap.previous_close}")
        return snap
