# QIF → QFX Converter for Quicken Mac

## When to use this skill

Use this skill when the user needs to:
- Import QIF transaction data into an existing Quicken Mac account
- Convert a QIF export (from PayPal, Venmo, a bank, or any financial service) to QFX format
- Clean up QIF transaction data that has unwanted splits or balance issues
- Fill gaps in Quicken account history using exported data

## Entry Point

When invoked, guide the user through conversion interactively.

### Steps

1. **Find QIF files.** Run via Bash:
   `bash {skill_dir}/find-qif-files.sh`
   where `{skill_dir}` is `.claude/skills/qif-to-qfx`.
   The script scans `~/Downloads` for `*.QIF`, `*.qif`, and `*.zip` files.
   Output is one line per file: `ext|size|date|path` — or `NO_FILES` if none found.
   Also check for any file paths the user provided as arguments to the skill.

2. **Present files.** Use AskUserQuestion:
   - header: "QIF → QFX Converter"
   - If ANY files found (QIF or ZIP — do NOT filter or judge zip files by name):
     - question: "Found these files in ~/Downloads. Which would you like to convert?"
     - options: one per file found (label = filename, description = file size + date modified)
     - multiSelect: true
     - Do NOT editorialize about whether files "look like" financial exports. Present all results.
   - If script output is `NO_FILES`:
     - question: "No QIF or ZIP files found in ~/Downloads. Where is your file?"
     - options: "Type a path" — "I'll specify the file location"

3. **Ask source type.** Use AskUserQuestion:
   - header: "Source"
   - question: "Where was this exported from?"
   - options:
     - "PayPal" — "Auto-balance enabled (subscriptions need it)"
     - "Bank" — "No balancing needed (single-entry format)"
     - "Other" — "I'll specify the options"

4. **Configure based on source:**
   - **PayPal**: `--org PayPal` (auto-balance ON, acctid auto-derives to "PayPal - Import")
   - **Bank**: `--no-balance` — then ask:
     Use AskUserQuestion: question "What's the bank name? (used as label in Quicken)"
     header: "Bank name", options: ["Chase", "Wells Fargo", "Bank of America", "Citi"]
     Use their answer (or "Other" text) for `--org` (acctid auto-derives to "{name} - Import").
   - **Other**: ask what options they want.
   - Note: `--acctid` auto-derives from `--org` as "{org} - Import". Only pass `--acctid`
     explicitly if the user wants a custom account identifier.

5. **Build and confirm the command.** Show the full command that will be run. For multi-file,
   use `-o ~/Downloads/{source}-combined.qfx`. For single file, let it auto-name.
   Ask: "Run this command?" (yes/no).

6. **Run the conversion.** Execute the command via Bash from the skill directory:
   `python3 {skill_dir}/qif_to_qfx.py {args}`
   where `{skill_dir}` is this skill's base directory.

7. **Show results.** Display the script output. Then remind the user:
   "**To import into Quicken:** File → Import → Web Connect (.QFX) → change Action to **Link to existing account** → select your account → Accept All"

### Rules
- Always show the command before running it.
- For multiple QIF files from the same source, combine them with `-o` flag.
- Default output location is `~/Downloads/` alongside the input files.
- If the user provided a file path as an argument, skip step 1-2 and use that path directly.

---

## Background

QIF (Quicken Interchange Format) is a common export format from financial services, but Quicken Mac can only import QIF into **new** accounts — not existing ones. To import into an existing account, you need QFX (Web Connect) format.

Additionally, QIF exports often have problems:

1. **Splits**: Many services (especially PayPal) add $0.00 "Fee" split lines to every transaction, causing Quicken to display "Split" instead of the category name.

2. **Imbalanced**: Some services (especially PayPal) inconsistently include both sides of transactions. Subscription charges may appear as debits with no matching credit, so the file doesn't net to zero. Importing it throws off the account balance.

3. **Missing header**: Some QIF exports omit the `!Account` header block that Quicken requires.

## The converter script

`qif_to_qfx.py` in this skill directory handles all of the above in one step.

### What it does

1. **Adds missing `!Account` header** if the QIF file doesn't start with one
2. **Strips split lines** (`S` and `$` prefixed lines) so transactions import as single entries
3. **Auto-balances** by matching debits to credits by date+amount, then generating offsetting entries for anything unmatched (can be skipped with `--no-balance`)
4. **Outputs QFX** with proper OFX/SGML structure, INTU.BID 10898 (Chase, a known-working Web Connect partner), and deterministic FITIDs for duplicate prevention

### CLI Reference

```bash
# Single file
python3 qif_to_qfx.py <input.qif> [output.qfx] [--no-balance] [--org NAME]

# Multiple files (combines and deduplicates)
python3 qif_to_qfx.py <input1.qif> <input2.qif> [...] -o <output.qfx> [--no-balance] [--org NAME]

# Zip file containing QIF files (auto-extracted)
python3 qif_to_qfx.py <exports.zip> -o <output.qfx> [--no-balance] [--org NAME]
```

**Options:**
- `-o FILE` — Output file path. **Required** when using multiple input files. Optional for single file.
- `--no-balance` — Skip the auto-balancing step. Use when the source QIF already nets to zero.
- `--org NAME` — Set the institution name in the QFX header (default: "Import"). Cosmetic only.
- `--acctid ID` — Set the account identifier (default: "Import"). **Use a unique value per source** so Quicken doesn't mix accounts when importing from multiple services.

If output path is omitted (single file mode), writes to `<input>-clean.qfx` in the same directory.

**Multi-file mode:** When multiple input files are provided, the script parses all files, deduplicates transactions across them (matching on date + amount + payee), and writes a single combined QFX output.

**Zip support:** `.zip` files are automatically extracted — all `.qif` files inside are parsed and deduplicated. You can mix `.zip` and `.qif` inputs freely.

### Import into Quicken

1. File → Import → Web Connect (.QFX)
2. Change Action from "Add" to **"Link to existing account"**
3. Select the target account
4. Continue → Accept All

## Expected output

```
Reading: ~/Downloads/Download.QIF
  Added missing !Account header
  Parsed: 943 transactions (splits stripped)
  Date range: 01/01/2025 – 12/31/2025
  Debits: $-54,722.35  Credits: $35,076.41  Net: $-19,645.94
  Balancing entries added: 407
  Final net: $0.00

Written: ~/Downloads/Download-clean.qfx
  Total transactions: 1350

Import: File → Import → Web Connect (.QFX) → Link to existing account
```

## Known source-specific behavior

### PayPal
- QIF export has double-entry structure: most purchases appear as a debit + a matching "General Card Deposit" credit, but subscriptions (Netflix, Spotify, Hulu, NYT, etc.) and donations only have the debit. Auto-balancing fixes this.
- Contains duplicate "authorization + completion" entries (e.g., "General Authorization" + "PreApproved Payment Bill User Payment" for the same charge). These pair up naturally — no special handling needed.
- PayPal QIF downloads cover up to 7 years but max 12 months per download. For longer periods, download multiple files and use multi-file mode: `python3 qif_to_qfx.py jan.QIF feb.QIF mar.QIF -o combined.qfx --org PayPal`. Overlapping transactions are automatically deduplicated.

### Venmo
- Not yet tested. QIF structure may differ. Report any issues.

### Banks
- Most bank QIF exports are straightforward single-entry. Use `--no-balance` since there's no double-entry to balance.

## Important notes

- **Python 3.6+** required (f-strings). No external dependencies.
- **INTU.BID 10898** (Chase) is used because it's a known-working Web Connect partner. Alternative: 2200. The actual institution doesn't matter — it only affects which label Quicken shows during import. The `--org` flag sets the display name but doesn't change the INTU.BID.
- **QFX does not support categories.** Quicken uses its renaming rules / QuickFill rules to assign categories based on payee names.
- **FITIDs are deterministic** (MD5 of date + amount + payee + index), so re-importing the same file won't create duplicates.
- **Idempotent on splits**: The script handles both raw QIF files (with splits) and pre-cleaned files (splits already removed).

## Troubleshooting

**"Quicken is currently unable to verify the financial institution information"**
- Quicken needs an internet connection to validate the INTU.BID during QFX import.

**Balance not zero after import**
- Check if the user concatenated multiple QIF downloads with overlapping date ranges — real duplicates break the balancer.
- The script prints the final net; if it's not $0.00, there's a data issue in the source QIF.

**Transactions showing as "Split" in Quicken**
- Some Quicken versions re-introduce splits during QFX import for certain transaction patterns. Cosmetic only — amounts and payees are correct.

**Account shows wrong balance after import**
- Did the user change Action to "Link to existing account"? If they left it as "Add", it created a new account instead.
- For sources like PayPal that need balancing, make sure `--no-balance` was NOT used.


