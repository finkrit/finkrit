# finkrit/packages/finq/datatype/market.py
from enum import Enum


class Exchange(Enum):
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"

    TSX = "TSX"              # Toronto Stock Exchange
    TSXV = "TSXV"            # TSX Venture Exchange

    LSE = "LSE"              # London Stock Exchange
    EUREX = "EUREX"

    HKEX = "HKEX"            # Hong Kong Stock Exchange
    SSE = "SSE"              # Shanghai Stock Exchange
    SZSE = "SZSE"            # Shenzhen Stock Exchange
    TSE = "TSE"              # Tokyo Stock Exchange

    NSE = "NSE"              # National Stock Exchange of India
    BSE = "BSE"              # Bombay Stock Exchange

    ASX = "ASX"              # Australian Securities Exchange

    SIX = "SIX"              # SIX Swiss Exchange

    CME = "CME"              # Chicago Mercantile Exchange
    CBOE = "CBOE"            # Chicago Board Options Exchange
    ICE = "ICE"              # Intercontinental Exchange
    

class MarketIndex(Enum):
    SP500 = ("^GSPC", "S&P 500")
    NASDAQ = ("^IXIC", "NASDAQ Composite")
    DOW = ("^DJI", "Dow Jones Industrial Average")
    WILSHIRE5000 = ("^W5000", "Wilshire 5000")
    SPY = ("SPY", "S&P 500 ETF")
    VOO = ("VOO", "S&P 500 ETF")
    VTI = ("VTI", "Total U.S. Stock Market ETF")
    QQQ = ("QQQ", "NASDAQ-100 ETF")
    IWM = ("IWM", "Russell 2000 ETF")

    def __init__(self, ticker: str, description: str):
        self.ticker = ticker
        self.description = description

