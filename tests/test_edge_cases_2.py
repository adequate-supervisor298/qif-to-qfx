"""Additional edge case tests: memo, dedup across files."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qif_to_qfx import write_qfx, parse_qif_files

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


class TestEdgeCases2:
    def test_memo_omitted_when_empty(self):
        txns = [{"date": "01/01/2025", "amount": -10.00, "payee": "Test", "memo": ""}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.qfx")
            write_qfx(txns, path)
            with open(path) as f:
                content = f.read()
            assert "<MEMO>" not in content

    def test_dedup_across_files(self):
        txns = parse_qif_files([fixture("dedup_file_a.qif"), fixture("dedup_file_b.qif")])
        assert len(txns) == 3
        payees = [t["payee"] for t in txns]
        assert payees.count("Netflix") == 1
        assert "Amazon" in payees
        assert "Target" in payees


class TestScanDownloads:
    def test_finds_qif_and_zip_files(self):
        from qif_to_qfx import scan_downloads
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "data.qif"), "w").close()
            open(os.path.join(tmpdir, "archive.zip"), "w").close()
            open(os.path.join(tmpdir, "readme.txt"), "w").close()
            found = scan_downloads(tmpdir)
            names = [os.path.basename(f) for f in found]
            assert "data.qif" in names
            assert "archive.zip" in names
            assert "readme.txt" not in names

    def test_returns_empty_for_missing_directory(self):
        from qif_to_qfx import scan_downloads
        found = scan_downloads("/nonexistent/path/xyz")
        assert found == []
