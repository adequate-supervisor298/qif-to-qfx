"""Tests for balance_transactions."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qif_to_qfx import balance_transactions, parse_qif

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


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

    def test_already_balanced_unchanged(self):
        txns = [
            {"date": "05/01/2025", "amount": -25.00, "payee": "Purchase"},
            {"date": "05/01/2025", "amount": 25.00, "payee": "Deposit"},
        ]
        balanced = balance_transactions(txns)
        assert len(balanced) == 2
        total = sum(t["amount"] for t in balanced)
        assert abs(total) < 0.01

    def test_unmatched_credits_get_offsetting_debits(self):
        txns = [
            {"date": "05/01/2025", "amount": 50.00, "payee": "Refund"},
            {"date": "05/02/2025", "amount": 25.00, "payee": "Cashback"},
        ]
        balanced = balance_transactions(txns)
        total = sum(t["amount"] for t in balanced)
        assert abs(total) < 0.01
        assert len(balanced) == 4

    def test_offsetting_credit_category(self):
        txns = [{"date": "05/05/2025", "amount": -9.99, "payee": "Hulu"}]
        balanced = balance_transactions(txns)
        generated = [t for t in balanced if t["amount"] > 0]
        assert generated[0]["category"] == "General Card Deposit"

    def test_offsetting_debit_category(self):
        txns = [{"date": "05/01/2025", "amount": 50.00, "payee": "Refund"}]
        balanced = balance_transactions(txns)
        generated = [t for t in balanced if t["amount"] < 0]
        assert generated[0]["category"] == "General Card Withdrawal"

    def test_paypal_fixture_nets_to_zero(self):
        txns = parse_qif(os.path.join(os.path.dirname(__file__), "fixtures", "paypal_double_entry.qif"))
        balanced = balance_transactions(txns)
        total = sum(t["amount"] for t in balanced)
        assert abs(total) < 0.01
