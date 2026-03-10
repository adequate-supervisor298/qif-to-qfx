"""Unit tests for the core QIF→QFX conversion pipeline."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qif_to_qfx import ensure_account_header, parse_qif, balance_transactions

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


class TestEnsureAccountHeader:
    def test_adds_header_when_missing(self):
        content = "!Type:Bank\nD01/01/2025\nT-10.00\nPTest\n^\n"
        result = ensure_account_header(content)
        assert result.startswith("!Account\n")
        assert "!Type:Bank" in result

    def test_preserves_existing_header(self):
        content = "!Account\nNChecking\nTBank\n^\n!Type:Bank\nD01/01/2025\nT-10.00\n^\n"
        result = ensure_account_header(content)
        assert result == content


class TestSplitStripping:
    def test_splits_stripped_from_transactions(self):
        txns = parse_qif(fixture("with_splits.qif"))
        assert len(txns) == 2
        assert txns[0]["payee"] == "Online Purchase"
        assert txns[0]["amount"] == -50.00


class TestBalanceTransactions:
    def test_unmatched_debits_get_offsetting_credits(self):
        txns = [
            {"date": "05/05/2025", "amount": -9.99, "payee": "Hulu"},
            {"date": "05/10/2025", "amount": -14.99, "payee": "NYT"},
        ]
        balanced = balance_transactions(txns)
        total = sum(t["amount"] for t in balanced)
        assert abs(total) < 0.01
        assert len(balanced) == 4
