"""Tests for qif_to_qfx multi-file and deduplication support."""

import os
import tempfile
from qif_to_qfx import deduplicate_transactions, parse_qif_files


class TestDeduplicateTransactions:
    def test_removes_exact_duplicates(self):
        txns = [
            {"date": "01/15/2025", "amount": -9.99, "payee": "Netflix"},
            {"date": "01/15/2025", "amount": -9.99, "payee": "Netflix"},
            {"date": "01/20/2025", "amount": -5.00, "payee": "Spotify"},
        ]
        result = deduplicate_transactions(txns)
        assert len(result) == 2
        assert result[0]["payee"] == "Netflix"
        assert result[1]["payee"] == "Spotify"

    def test_preserves_different_amounts_same_payee(self):
        txns = [
            {"date": "01/15/2025", "amount": -9.99, "payee": "Netflix"},
            {"date": "01/15/2025", "amount": -15.99, "payee": "Netflix"},
        ]
        result = deduplicate_transactions(txns)
        assert len(result) == 2

    def test_handles_missing_payee(self):
        """Transactions without payee should still dedup on date+amount."""
        txns = [
            {"date": "01/15/2025", "amount": -9.99},
            {"date": "01/15/2025", "amount": -9.99},
            {"date": "01/15/2025", "amount": -5.00},
        ]
        result = deduplicate_transactions(txns)
        assert len(result) == 2
