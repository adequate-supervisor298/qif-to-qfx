"""Tests for FITID determinism."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import tempfile

from qif_to_qfx import make_fitid, parse_qif, write_qfx

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestFitidDeterminism:
    def test_same_input_same_fitid(self):
        txn = {"date": "01/15/2025", "amount": -42.50, "payee": "Grocery Store"}
        assert make_fitid(txn, 0) == make_fitid(txn, 0)

    def test_different_index_different_fitid(self):
        txn = {"date": "01/15/2025", "amount": -42.50, "payee": "Grocery Store"}
        assert make_fitid(txn, 0) != make_fitid(txn, 1)

    def test_different_amount_different_fitid(self):
        txn1 = {"date": "01/15/2025", "amount": -42.50, "payee": "Store"}
        txn2 = {"date": "01/15/2025", "amount": -42.51, "payee": "Store"}
        assert make_fitid(txn1, 0) != make_fitid(txn2, 0)

    def test_fitid_is_24_chars(self):
        txn = {"date": "01/01/2025", "amount": -10.00, "payee": "Test"}
        assert len(make_fitid(txn, 0)) == 24

    def test_full_file_produces_stable_fitids(self):
        import re
        txns = parse_qif(os.path.join(FIXTURES, "basic_bank.qif"))
        with tempfile.TemporaryDirectory() as tmpdir:
            out1 = os.path.join(tmpdir, "run1.qfx")
            out2 = os.path.join(tmpdir, "run2.qfx")
            write_qfx(txns, out1)
            write_qfx(txns, out2)
            with open(out1) as f:
                c1 = f.read()
            with open(out2) as f:
                c2 = f.read()
            assert re.findall(r"<FITID>(\w+)", c1) == re.findall(r"<FITID>(\w+)", c2)
