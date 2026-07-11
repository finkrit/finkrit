# finkrit/packages/finq/datatype/assettype.py
from enum import Enum

class AssetType(Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    BOND = "bond"
    