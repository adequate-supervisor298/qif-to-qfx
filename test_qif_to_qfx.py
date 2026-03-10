"""Tests for qif_to_qfx multi-file and deduplication support."""

import os
import sys
import tempfile
import zipfile
import zipfile
from qif_to_qfx import deduplicate_transactions, parse_qif_files


def write_qif(dir_path, filename, transactions):
    """Write a minimal QIF file from a list of (date, amount, payee) tuples."""
    path = os.path.join(dir_path, filename)
    with open(path, "w") as f:
        f.write("!Account\nNTest\nTCash\n^\n")
        for date, amount, payee in transactions:
            f.write(f"D{date}\nT{amount:.2f}\nP{payee}\n^\n")
    return path


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


class TestParseQifFiles:
    def test_combines_two_files_and_deduplicates(self):
        """Two QIF files with an overlapping Netflix txn should produce 3 unique transactions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = write_qif(tmpdir, "bank1.qif", [
                ("01/15/2025", -9.99, "Netflix"),
                ("01/20/2025", -5.99, "Spotify"),
            ])
            file2 = write_qif(tmpdir, "bank2.qif", [
                ("01/15/2025", -9.99, "Netflix"),  # duplicate
                ("01/25/2025", -7.99, "Hulu"),
            ])
            result = parse_qif_files([file1, file2])
            assert len(result) == 3
            payees = [t["payee"] for t in result]
            assert "Netflix" in payees
            assert "Spotify" in payees
            assert "Hulu" in payees


    def test_parse_qif_files_from_zip(self):
        """A .zip containing two QIF files should be extracted, parsed, and deduped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            qif1 = "!Account\nNTest\nTCash\n^\nD01/15/2025\nT-9.99\nPNetflix\n^\nD01/20/2025\nT-5.99\nPSpotify\n^\n"
            qif2 = "!Account\nNTest\nTCash\n^\nD01/15/2025\nT-9.99\nPNetflix\n^\nD01/25/2025\nT-7.99\nPHulu\n^\n"

            zip_path = os.path.join(tmpdir, "exports.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("bank1.qif", qif1)
                zf.writestr("bank2.qif", qif2)

            result = parse_qif_files([zip_path])
            assert len(result) == 3
            payees = [t["payee"] for t in result]
            assert "Netflix" in payees
            assert "Spotify" in payees
            assert "Hulu" in payees


class TestCliMultiFile:
    def test_cli_multiple_inputs_with_output_flag(self):
        """CLI should accept multiple input files and -o for output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = write_qif(tmpdir, "a.qif", [
                ("03/01/2025", -10.00, "Netflix"),
            ])
            file2 = write_qif(tmpdir, "b.qif", [
                ("03/01/2025", -10.00, "Netflix"),  # duplicate
                ("03/05/2025", -6.00, "Hulu"),
            ])
            output = os.path.join(tmpdir, "combined.qfx")
            sys.argv = ["qif_to_qfx.py", file1, file2, "-o", output, "--no-balance"]

            from qif_to_qfx import main
            main()

            assert os.path.exists(output)
            with open(output) as f:
                content = f.read()
            # Should have 2 unique transactions (Netflix deduped)
            assert content.count("<STMTTRN>") == 2

    def test_cli_date_range_sorts_chronologically(self, capsys):
        """Date range display should sort by actual date, not string order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = write_qif(tmpdir, "a.qif", [
                ("12/31/2024", -10.00, "OldTxn"),
                ("01/03/2026", -5.00, "NewTxn"),
            ])
            output = os.path.join(tmpdir, "out.qfx")
            sys.argv = ["qif_to_qfx.py", file1, "-o", output, "--no-balance"]

            from qif_to_qfx import main
            main()

            captured = capsys.readouterr()
            assert "12/31/2024" in captured.out.split("Date range:")[1].split("–")[0]
            assert "01/03/2026" in captured.out.split("Date range:")[1].split("\n")[0]

    def test_cli_with_zip_input(self):
        """CLI should accept a .zip file containing QIF files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            qif1 = "!Account\nNTest\nTCash\n^\nD04/01/2025\nT-15.00\nPAmazon\n^\n"
            qif2 = "!Account\nNTest\nTCash\n^\nD04/05/2025\nT-8.00\nPTarget\n^\n"
            zip_path = os.path.join(tmpdir, "exports.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("file1.qif", qif1)
                zf.writestr("file2.qif", qif2)

            output = os.path.join(tmpdir, "out.qfx")
            sys.argv = ["qif_to_qfx.py", zip_path, "-o", output, "--no-balance"]

            from qif_to_qfx import main
            main()

            assert os.path.exists(output)
            with open(output) as f:
                content = f.read()
            assert content.count("<STMTTRN>") == 2
