# finkrit/packages/finkritq/tests/portfolio/test_portfolio.py
from __future__ import annotations

from datetime import date

from finkritq.portfolio import Portfolio


class TestPortfolio:

    def test_add_position(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")

        returned = portfolio.add_position(position)

        assert returned is position
        assert portfolio.position_count == 1

    def test_add_duplicate_position_returns_existing(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")

        portfolio.add_position(position)
        returned = portfolio.add_position(position)

        assert returned is position
        assert portfolio.position_count == 1

    def test_remove_position(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_position(position)

        removed = portfolio.remove_position(position.id)

        assert removed is position
        assert portfolio.position_count == 0

    def test_remove_missing_position_returns_none(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.remove_position("missing") is None

    def test_get_position(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_position(position)

        assert portfolio.get_position(position.id) is position

    def test_get_missing_position_returns_none(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.get_position("missing") is None

    def test_has_position_true(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_position(position)

        assert portfolio.has_position(position.id)

    def test_has_position_false(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert not portfolio.has_position("missing")

    def test_positions(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.positions == [position]

    def test_assets(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.assets == (position.asset,)

    def test_lots(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.lots == tuple(position.lots)

    def test_cost_basis(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.cost_basis == position.cost_basis

    def test_position_count(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.position_count == 0

        portfolio.add_position(position)

        assert portfolio.position_count == 1

    def test_asset_count(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.asset_count == len(portfolio.assets)

    def test_lot_count(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.lot_count == len(portfolio.lots)

    def test_is_empty_true(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.is_empty

    def test_is_empty_false(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert not portfolio.is_empty

    def test_long_term_lots(self, position):
        # The fixture position's lot is acquired at LONG_TERM_DATE (2020).
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        as_of = date(2025, 1, 1)
        assert all(lot.is_long_term(as_of) for lot in portfolio.long_term_lots(as_of))

    def test_short_term_lots(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        as_of = date(2025, 1, 1)
        assert all(not lot.is_long_term(as_of) for lot in portfolio.short_term_lots(as_of))

    def test_earliest_acquired(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.earliest_acquired == min(lot.acquired for lot in portfolio.lots)

    def test_latest_acquired(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert portfolio.latest_acquired == max(lot.acquired for lot in portfolio.lots)

    def test_iter(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert list(portfolio) == [position]

    def test_len(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert len(portfolio) == 0

        portfolio.add_position(position)

        assert len(portfolio) == 1

    def test_contains(self, position):
        portfolio = Portfolio(id="1", name="Portfolio", positions=[position])

        assert position in portfolio

    def test_not_contains(self, position):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert position not in portfolio

    def test_str(self):
        portfolio = Portfolio(id="1", name="Retirement")

        assert str(portfolio) == "Retirement"

    def test_repr(self):
        portfolio = Portfolio(id="1", name="Retirement")

        assert repr(portfolio) == "Portfolio(name='Retirement', positions=0)"

    def test_optional_fields_are_stored(self):
        portfolio = Portfolio(
            id="1",
            name="Portfolio",
            notes="Long-term portfolio",
        )

        assert portfolio.notes == "Long-term portfolio"
