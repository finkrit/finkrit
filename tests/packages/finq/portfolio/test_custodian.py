# finkrit/tests/packages/finq/portfolio/test_custodian.py
from __future__ import annotations

import pytest

from packages.finq.portfolio.custodian import Custodian
from packages.finq.datatype import CustodianType


class TestCustodian:

    @pytest.mark.parametrize("custodian_type", [
        t for t in CustodianType
        if t is not CustodianType.OTHER
    ])
    def test_name_matches_enum_value(self, custodian_type):
        custodian = Custodian(custodian_type)
        assert custodian.name == custodian_type.value

    def test_custom_name_used_for_other(self):
        custodian = Custodian(
            CustodianType.OTHER,
            note="Local Credit Union",
        )
        assert custodian.name == "Local Credit Union"

    def test_other_without_note_uses_enum_value(self):
        custodian = Custodian(CustodianType.OTHER)
        assert custodian.name == CustodianType.OTHER.value

    def test_is_custom_true_for_other(self):
        custodian = Custodian(CustodianType.OTHER)
        assert custodian.is_custom is True

    @pytest.mark.parametrize("custodian_type", [t for t in CustodianType if t is not CustodianType.OTHER])
    def test_is_custom_false_for_standard_types(self, custodian_type):
        custodian = Custodian(custodian_type)
        assert custodian.is_custom is False

    def test_note_is_stored(self):
        custodian = Custodian(
            CustodianType.OTHER,
            note="Employer Retirement Plan",
        )
        assert custodian.note == "Employer Retirement Plan"

    def test_dataclass_is_mutable(self):
        custodian = Custodian(CustodianType.OTHER)
        custodian.note = "Brokerage Account"
        assert custodian.note == "Brokerage Account"

