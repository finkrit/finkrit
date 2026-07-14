# finkrit/packages/finkritq/datatype/custodian.py
from enum import StrEnum


class CustodianType(StrEnum):
    SCHWAB = "Charles Schwab"
    FIDELITY = "Fidelity"
    VANGUARD = "Vanguard"
    PERSHING = "Pershing"
    INTERACTIVE_BROKERS = "Interactive Brokers"
    ALTRUIST = "Altruist"
    APEX = "Apex Clearing"
    TRADEPMR = "TradePMR"
    ETRADE = "E*TRADE"
    OTHER = "Other"

