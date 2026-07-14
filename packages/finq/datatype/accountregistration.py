from enum import StrEnum

class AccountRegistrationType(StrEnum):
    INDIVIDUAL = "Individual"
    JOINT = "Joint"

    TRADITIONAL_IRA = "Traditional IRA"
    ROTH_IRA = "Roth IRA"
    SEP_IRA = "SEP IRA"
    SIMPLE_IRA = "SIMPLE IRA"

    HSA = "Health Savings Account"
    COLLEGE_529 = "529 Plan"

    TRUST = "Trust"
    ESTATE = "Estate"

    CORPORATE = "Corporate"
    LLC = "Limited Liability Company"
    PARTNERSHIP = "Partnership"

    OTHER = "Other"

    