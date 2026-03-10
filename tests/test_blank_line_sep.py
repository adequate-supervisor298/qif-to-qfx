"""Test that QIF files using blank lines as record separators (e.g. Chase) parse correctly."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qif_to_qfx import parse_qif

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestBlankLineSeparator:
    def test_parses_all_transactions(self):
        txns = parse_qif(os.path.join(FIXTURES, "blank_line_sep.qif"))
        assert len(txns) == 3
        assert txns[0]["payee"] == "SQ *FEDERATION OF INDO-AM"
        assert txns[0]["amount"] == -10.00
        assert txns[1]["payee"] == "KING FALAFEL"
        assert txns[2]["payee"] == "GOODWILL #5244"
