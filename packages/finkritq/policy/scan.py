# finkrit/packages/finkritq/policy/scan.py
"""
Book-level supervision: run the policy checks across a set of portfolios and
surface the ones that need attention, worst first.

Supervision is not a one-portfolio question. A book has many accounts, and the
useful output is the exception list, which accounts have drifted out of their
bands, break a restriction, or no longer suit their risk tolerance. This scans a
collection of (portfolio, policy) pairs and returns only those exceptions,
ranked by total drift so the biggest offenders come first.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from finkritq.datatype import VaREstimationMethod
from finkritq.policy.compliance import PolicyStatus, policy_status
from finkritq.policy.policy import Policy
from finkritq.policy.suitability import Suitability, SuitabilityVerdict, suitability
from finkritq.portfolio import PortfolioData


@dataclass(frozen=True, slots=True)
class BookException:
    """One portfolio flagged during a book scan, with the reasons attached."""

    portfolio_id: str
    status: PolicyStatus
    suitability: Suitability | None   # None when the policy set no risk tolerance

    @property
    def needs_attention(self) -> bool:
        """
        True when the portfolio is out of compliance OR its risk no longer suits
        the tolerance. An on-model account can still be taking too much risk, so
        both are checked.
        """
        unsuitable = (
            self.suitability is not None
            and self.suitability.verdict is not SuitabilityVerdict.ALIGNED
        )
        return (not self.status.in_compliance) or unsuitable


def scan_book(
    items: Iterable[tuple[PortfolioData, Policy]],
    method: VaREstimationMethod = VaREstimationMethod.PARAMETRIC,
) -> list[BookException]:
    """
    Scan (portfolio, policy) pairs, returning the exceptions worst-drift first.

    For each portfolio it runs ``policy_status`` and, when the policy carries a
    risk tolerance, ``suitability`` (with ``method``). Only portfolios that need
    attention are returned. Portfolio identity comes from ``portfolio.id``.
    """
    exceptions: list[BookException] = []
    for portfolio_data, policy in items:
        status = policy_status(portfolio_data, policy)
        fit = None
        if policy.risk_tolerance is not None:
            fit = suitability(portfolio_data, policy.risk_tolerance, method=method)

        flagged = BookException(
            portfolio_id=portfolio_data.portfolio.id,
            status=status,
            suitability=fit,
        )
        if flagged.needs_attention:
            exceptions.append(flagged)

    exceptions.sort(key=lambda item: item.status.total_drift, reverse=True)
    return exceptions
