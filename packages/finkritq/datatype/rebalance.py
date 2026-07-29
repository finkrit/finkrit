# finkrit/packages/finkritq/datatype/rebalance.py
"""
Rebalance domain vocabulary, the parallel of datatype/tax.py.

Only dependency free enums belong here. The trade and plan dataclasses stay
beside their algorithms in optimize/, they carry Asset and lot types that would
cycle back into this package.
"""
from enum import Enum


class RebalanceSizing(Enum):
    """How far a triggered trade goes.

    The tolerance band decides WHETHER an asset trades. This decides WHERE the
    trade lands, and it is deliberately a separate axis: a nonzero tolerance
    with TO_TARGET still trades the full drift (see rebalance_to_model's
    docstring for the worked example).
    """

    # Value strings are stable identifiers (serialization / tool schemas); do not
    # rename without updating any persisted references.
    TO_TARGET = "to_target"        # trade the full drift, land on the model weight
    TO_BAND_EDGE = "to_band_edge"  # trade only the excess, land just inside the band
