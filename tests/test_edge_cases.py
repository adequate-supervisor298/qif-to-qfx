"""Tests for edge cases: non-ASCII, no payee, truncation, memo, dedup."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qif_to_qfx import parse_qif, write_qfx, escape_ofx, parse_qif_files

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


class TestEdgeCases:
    def test_non_ascii_payees_parse(self):
        txns = parse_qif(fixture("non_ascii.qif"))
        assert len(txns) == 3
        payees = [t["payee"] for t in txns]
        assert "Café René" in payees

    def test_non_ascii_in_qfx_output(self):
        txns = parse_qif(fixture("non_ascii.qif"))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.qfx")
            write_qfx(txns, path)
            with open(path) as f:
                content = f.read()
            assert "Caf" in content

    def test_no_payee_falls_back_to_unknown(self):
        txns = [{"date": "01/01/2025", "amount": -10.00}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.qfx")
            write_qfx(txns, path)
            with open(path) as f:
                content = f.read()
            assert "<NAME>Unknown" in content

    def test_single_transaction_file(self):
        txns = parse_qif(fixture("single_txn.qif"))
        assert len(txns) == 1
        assert txns[0]["payee"] == "Coffee"
        assert txns[0]["amount"] == -5.00

    def test_escape_ofx_special_chars(self):
        assert escape_ofx("AT&T") == "AT&amp;T"
        assert escape_ofx("A<B>C") == "A&lt;B&gt;C"

    def test_payee_truncated_to_32_chars(self):
        long_payee = "A" * 50
        txns = [{"date": "01/01/2025", "amount": -10.00, "payee": long_payee}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.qfx")
            write_qfx(txns, path)
            with open(path) as f:
                content = f.read()
            assert "<NAME>" + "A" * 32 in content
            assert "<NAME>" + "A" * 33 not in content

    def test_memo_included_when_present(self):
        txns = [{"date": "01/01/2025", "amount": -10.00, "payee": "Test", "memo": "ref#123"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.qfx")
            write_qfx(txns, path)
            with open(path) as f:
                content = f.read()
            assert "<MEMO>ref#123" in content
