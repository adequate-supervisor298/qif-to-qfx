"""Tests for interactive mode."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInteractiveMode:
    def test_interactive_builds_correct_command(self):
        from qif_to_qfx import interactive_mode
        with tempfile.TemporaryDirectory() as tmpdir:
            qif = os.path.join(tmpdir, "Download.QIF")
            with open(qif, "w") as f:
                f.write("!Account\nNTest\nTCash\n^\n!Type:Bank\nD01/01/2025\nT-10.00\nPTest\n^\n")
            # Simulate user input: select file "1", source "1" (PayPal), confirm "y"
            inputs = iter(["1", "1", "y"])
            result = interactive_mode(scan_dir=tmpdir, input_fn=lambda prompt: next(inputs))
            assert result is not None
            assert qif in result["input_paths"]
            assert result["org"] == "PayPal"
            assert result["no_balance"] is False

    def test_bank_source_sets_no_balance(self):
        from qif_to_qfx import interactive_mode
        with tempfile.TemporaryDirectory() as tmpdir:
            qif = os.path.join(tmpdir, "Bank.qif")
            with open(qif, "w") as f:
                f.write("!Account\nNTest\nTCash\n^\n!Type:Bank\nD01/01/2025\nT-10.00\nPTest\n^\n")
            inputs = iter(["1", "2", "y"])
            result = interactive_mode(scan_dir=tmpdir, input_fn=lambda prompt: next(inputs))
            assert result["org"] == "Bank"
            assert result["no_balance"] is True

    def test_cancel_returns_none(self):
        from qif_to_qfx import interactive_mode
        with tempfile.TemporaryDirectory() as tmpdir:
            qif = os.path.join(tmpdir, "test.qif")
            with open(qif, "w") as f:
                f.write("!Account\nNTest\nTCash\n^\n!Type:Bank\nD01/01/2025\nT-10.00\nPTest\n^\n")
            inputs = iter(["1", "1", "n"])
            result = interactive_mode(scan_dir=tmpdir, input_fn=lambda prompt: next(inputs))
            assert result is None

    def test_multi_file_selection(self):
        from qif_to_qfx import interactive_mode
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["a.qif", "b.qif"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("!Account\nNTest\nTCash\n^\n!Type:Bank\nD01/01/2025\nT-10.00\nPTest\n^\n")
            inputs = iter(["1,2", "1", "y"])
            result = interactive_mode(scan_dir=tmpdir, input_fn=lambda prompt: next(inputs))
            assert len(result["input_paths"]) == 2
            assert "PayPal-combined.qfx" in result["output_path"]

    def test_no_args_triggers_interactive_and_converts(self):
        from qif_to_qfx import main
        with tempfile.TemporaryDirectory() as tmpdir:
            qif = os.path.join(tmpdir, "test.qif")
            with open(qif, "w") as f:
                f.write("!Account\nNTest\nTCash\n^\n!Type:Bank\nD01/01/2025\nT-10.00\nPTest\n^\n")
            sys.argv = ["qif_to_qfx.py", "--interactive-scan-dir", tmpdir]
            import builtins
            original_input = builtins.input
            inputs = iter(["1", "2", "y"])
            builtins.input = lambda prompt="": next(inputs)
            try:
                main()
            finally:
                builtins.input = original_input
            expected = os.path.join(tmpdir, "test-clean.qfx")
            assert os.path.exists(expected)
