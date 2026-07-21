# finkrit/packages/finkritq/policy/__init__.py
"""
Policy: the target a portfolio is supervised against, and the checks that
measure a portfolio against it.

A Policy is pure specification (target weights, drift bands, holding
restrictions, risk tolerance), the generic math input for supervision. Binding a
policy to a particular owner is a concern for the layer above finq. This
package holds the data model (policy.py), the drift and restriction compliance
checks (compliance.py), and the risk-vs-tolerance suitability check
(suitability.py).
"""
from finkritq.policy.policy import (
    DriftBand,
    Policy,
    Restriction,
    RestrictionKind,
    RiskTolerance,
)
from finkritq.policy.compliance import (
    DriftBreach,
    PolicyStatus,
    RestrictionViolation,
    drift_breaches,
    policy_status,
    restriction_violations,
)
from finkritq.policy.suitability import (
    Suitability,
    SuitabilityVerdict,
    suitability,
)
from finkritq.policy.scan import (
    BookException,
    scan_book,
)

__all__ = [
    # policy model
    "Policy",
    "DriftBand",
    "Restriction",
    "RestrictionKind",
    "RiskTolerance",
    # compliance
    "drift_breaches",
    "restriction_violations",
    "policy_status",
    "DriftBreach",
    "RestrictionViolation",
    "PolicyStatus",
    # suitability
    "suitability",
    "Suitability",
    "SuitabilityVerdict",
    # book scan
    "scan_book",
    "BookException",
]
