"""Tests for QFX output structure."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qif_to_qfx import parse_qif, write_qfx

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


def write_and_read(txns, **kwargs):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "out.qfx")
        write_qfx(txns, path, **kwargs)
        with open(path) as f:
            return f.read()


class TestQfxStructure:
    def test_contains_ofx_header(self):
        txns = parse_qif(fixture("basic_bank.qif"))
        content = write_and_read(txns)
        assert "OFXHEADER:100" in content
        assert "DATA:OFXSGML" in content

    def test_contains_bank_message(self):
        txns = parse_qif(fixture("basic_bank.qif"))
        content = write_and_read(txns)
        assert "<BANKMSGSRSV1>" in content
        assert "</BANKMSGSRSV1>" in content

    def test_contains_stmttrn_count(self):
        txns = parse_qif(fixture("basic_bank.qif"))
        content = write_and_read(txns)
        assert content.count("<STMTTRN>") == 3

    def test_contains_ledgerbal(self):
        txns = parse_qif(fixture("basic_bank.qif"))
        content = write_and_read(txns)
        assert "<LEDGERBAL>" in content
        assert "<BALAMT>" in content

    def test_date_range_in_banktranlist(self):
        txns = parse_qif(fixture("basic_bank.qif"))
        content = write_and_read(txns)
        assert "<DTSTART>20250115000000" in content
        assert "<DTEND>20250125235959" in content

    def test_org_and_acctid(self):
        txns = parse_qif(fixture("single_txn.qif"))
        content = write_and_read(txns, account_id="PayPal", org="PayPal")
        assert "<ORG>PayPal" in content
        assert "<ACCTID>PayPal" in content

    def test_uses_name_tag(self):
        txns = parse_qif(fixture("basic_bank.qif"))
        content = write_and_read(txns)
        assert "<NAME>Grocery Store" in content
