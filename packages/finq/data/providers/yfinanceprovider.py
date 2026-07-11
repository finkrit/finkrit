# finkrit/packages/finq/data/providers/yfinanceprovider.py

from packages.finq.asset import Asset, AssetSnapshot
from packages.finq.data.interfaces import HistoryProvider, SnapshotProvider
from packages.finq.datatype import PriceHistory


from datetime import date
from loguru import logger
import numpy as np
import pandas as pd
import yfinance as yf

class YFinanceProvider(HistoryProvider, SnapshotProvider):

    def history(
        self,
        asset: Asset,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> PriceHistory:
        
        logger.info(f"Fetching history for asset: {asset.ticker}")

        df = yf.download(
            tickers=asset.ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

        if df.empty:
            raise ValueError(
                f"No historical data found for '{asset.ticker}'."
            )

        logger.info(f"Done fetching history for asset: {asset.ticker}")
        return self._to_price_history(df)


    @staticmethod
    def _to_price_history(df: pd.DataFrame) -> PriceHistory:

        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(-1, axis=1)

        return PriceHistory(
            dates=df.index.to_numpy(dtype="datetime64[ns]"),
            open=df["Open"].to_numpy(dtype=np.float64),
            high=df["High"].to_numpy(dtype=np.float64),
            low=df["Low"].to_numpy(dtype=np.float64),
            close=df["Close"].to_numpy(dtype=np.float64),
            volume=df["Volume"].to_numpy(dtype=np.int64),
        )
    

    def snapshot(self, asset: Asset):
        logger.info(f"Fetching snapshot for asset: {asset.ticker}")
        
        info = yf.Ticker(asset.ticker).fast_info

        logger.info(f"Done fetching snapshot for asset: {asset.ticker}")
        return AssetSnapshot(
            asset=asset,
            last_price=info.last_price,
            previous_close=info.previous_close,
        )
        
