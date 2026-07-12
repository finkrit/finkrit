from enum import Enum

class VaREstimationMethod(Enum):
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"
    PARAMETRIC = "parametric"
    
    