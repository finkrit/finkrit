from __future__ import annotations

from decimal import Decimal

from packages.finq.portfolio import Portfolio


class TestPortfolio:

    def test_add_account(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")

        returned = portfolio.add_account(account)

        assert returned is account
        assert portfolio.account_count == 1

    def test_add_duplicate_account_returns_existing(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")

        portfolio.add_account(account)
        returned = portfolio.add_account(account)

        assert returned is account
        assert portfolio.account_count == 1

    def test_remove_account(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        removed = portfolio.remove_account(account.id)

        assert removed is account
        assert portfolio.account_count == 0

    def test_remove_missing_account_returns_none(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.remove_account("missing") is None

    def test_get_account(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.get_account(account.id) is account

    def test_get_missing_account_returns_none(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.get_account("missing") is None

    def test_has_account_true(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.has_account(account.id)

    def test_has_account_false(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert not portfolio.has_account("missing")

    def test_positions(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.positions == tuple(account)

    def test_assets(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.assets == tuple(position.asset for position in account)

    def test_lots(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        expected = tuple(lot for position in account for lot in position.lots)

        assert portfolio.lots == expected

    def test_cost_basis(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.cost_basis == account.cost_basis

    def test_account_count(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.account_count == 0

        portfolio.add_account(account)

        assert portfolio.account_count == 1

    def test_position_count(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.position_count == len(portfolio.positions)

    def test_asset_count(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.asset_count == len(portfolio.assets)

    def test_lot_count(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.lot_count == len(portfolio.lots)

    def test_is_empty_true(self):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert portfolio.is_empty

    def test_is_empty_false(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert not portfolio.is_empty

    def test_long_term_lots(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert all(lot.is_long_term for lot in portfolio.long_term_lots)

    def test_short_term_lots(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert all(not lot.is_long_term for lot in portfolio.short_term_lots)

    def test_earliest_acquired(self, account, position):
        account.add_position(position)
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.earliest_acquired == min(
            lot.acquired for lot in portfolio.lots
        )

    def test_latest_acquired(self, account, position):
        account.add_position(position)
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert portfolio.latest_acquired == max(
            lot.acquired for lot in portfolio.lots
        )

    def test_iter(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert list(portfolio) == [account]

    def test_len(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert len(portfolio) == 0

        portfolio.add_account(account)

        assert len(portfolio) == 1

    def test_contains(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")
        portfolio.add_account(account)

        assert account in portfolio

    def test_not_contains(self, account):
        portfolio = Portfolio(id="1", name="Portfolio")

        assert account not in portfolio

    def test_str(self):
        portfolio = Portfolio(id="1", name="Retirement")

        assert str(portfolio) == "Retirement"

    def test_repr(self):
        portfolio = Portfolio(id="1", name="Retirement")

        assert repr(portfolio) == (
            "Portfolio(name='Retirement', accounts=0, positions=0)"
        )

    def test_optional_fields_are_stored(self):
        user = object()

        portfolio = Portfolio(
            id="1",
            name="Portfolio",
            user=user,
            notes="Long-term portfolio",
        )

        assert portfolio.user is user
        assert portfolio.notes == "Long-term portfolio"

