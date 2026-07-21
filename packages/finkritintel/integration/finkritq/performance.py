from __future__ import annotations

from finkritq.anal.performance import (
    portfolio_annualized_return,
    portfolio_calmar_ratio,
    portfolio_sharpe_ratio,
    portfolio_sortino_ratio,
    portfolio_total_return,
)

from finkritintel.tool.binding import ToolBinding
from finkritintel.tool.performance import (
    PORTFOLIO_ANNUALIZED_RETURN,
    PORTFOLIO_CALMAR_RATIO,
    PORTFOLIO_SHARPE_RATIO,
    PORTFOLIO_SORTINO_RATIO,
    PORTFOLIO_TOTAL_RETURN,
)
from finkritintel.integration.finkritq.performance_schema import (
    AnnualizedReturnInput,
    CalmarRatioInput,
    SharpeRatioInput,
    SortinoRatioInput,
    TotalReturnInput,
)


PORTFOLIO_TOTAL_RETURN_BINDING = ToolBinding(
    contract=PORTFOLIO_TOTAL_RETURN,
    input_schema=TotalReturnInput,
    output_schema=float,
    implementation=portfolio_total_return,
)

PORTFOLIO_ANNUALIZED_RETURN_BINDING = ToolBinding(
    contract=PORTFOLIO_ANNUALIZED_RETURN,
    input_schema=AnnualizedReturnInput,
    output_schema=float,
    implementation=portfolio_annualized_return,
)

PORTFOLIO_SHARPE_RATIO_BINDING = ToolBinding(
    contract=PORTFOLIO_SHARPE_RATIO,
    input_schema=SharpeRatioInput,
    output_schema=float,
    implementation=portfolio_sharpe_ratio,
)

PORTFOLIO_SORTINO_RATIO_BINDING = ToolBinding(
    contract=PORTFOLIO_SORTINO_RATIO,
    input_schema=SortinoRatioInput,
    output_schema=float,
    implementation=portfolio_sortino_ratio,
)

PORTFOLIO_CALMAR_RATIO_BINDING = ToolBinding(
    contract=PORTFOLIO_CALMAR_RATIO,
    input_schema=CalmarRatioInput,
    output_schema=float,
    implementation=portfolio_calmar_ratio,
)
