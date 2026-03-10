# QIF → QFX Converter for Quicken Mac

## When to use this skill

Use this skill when the user needs to:
- Import QIF transaction data into an existing Quicken Mac account
- Convert a QIF export (from PayPal, Venmo, a bank, or any financial service) to QFX format
- Clean up QIF transaction data that has unwanted splits or balance issues
- Fill gaps in Quicken account history using exported data

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

### Usage

```bash
python3 qif_to_qfx.py <input.qif> [output.qfx] [--no-balance] [--org NAME]
```

**Options:**
- `--no-balance` — Skip the auto-balancing step. Use when the source QIF already nets to zero.
- `--org NAME` — Set the institution name in the QFX header (default: "Import"). Cosmetic only.
- `--acctid ID` — Set the account identifier (default: "Import"). **Use a unique value per source** so Quicken doesn't mix accounts when importing from multiple services.

If output path is omitted, writes to `<input>-clean.qfx` in the same directory.

### Examples

```bash
# PayPal export (needs balancing — subscriptions have no matching credits)
python3 qif_to_qfx.py ~/Downloads/Download.QIF ~/Downloads/PayPal-import.qfx --org PayPal

# Bank export that already balances
python3 qif_to_qfx.py ~/Downloads/BankExport.qif --no-balance --org "My Bank" --acctid MyBank

# Multiple sources — use different acctid for each
python3 qif_to_qfx.py ~/Downloads/PayPal.QIF --org PayPal --acctid PayPal
python3 qif_to_qfx.py ~/Downloads/Venmo.QIF --org Venmo --acctid Venmo --no-balance

# Simple conversion, auto-detect everything
python3 qif_to_qfx.py ~/Downloads/Download.QIF
```

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
- PayPal QIF downloads cover up to 7 years but max 12 months per download. For longer periods, download multiple files, concatenate, then convert.

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
