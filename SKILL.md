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

### Examples

```bash
# PayPal export (needs balancing — subscriptions have no matching credits)
python3 qif_to_qfx.py ~/Downloads/Download.QIF ~/Downloads/PayPal-import.qfx --org PayPal

# Bank export that already balances
python3 qif_to_qfx.py ~/Downloads/BankExport.qif --no-balance --org "My Bank" --acctid MyBank

# Combine multiple QIF files with deduplication
python3 qif_to_qfx.py ~/Downloads/PayPal-Jan.QIF ~/Downloads/PayPal-Feb.QIF -o ~/Downloads/PayPal-combined.qfx --org PayPal

# Convert from a zip file containing QIF exports
python3 qif_to_qfx.py ~/Downloads/exports.zip -o ~/Downloads/combined.qfx --org PayPal --no-balance

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

---

## Roadmap: Expanding to a Universal Financial File Converter

This tool is evolving into a comprehensive, open-source, bidirectional converter for financial transaction files — banking AND investment/brokerage — across QIF, QFX/OFX, and CSV formats. The goal is to become the only open-source tool that handles investment transactions, filling a gap where every existing project stops at banking.

### Why this matters

- **No open-source bidirectional QIF ↔ OFX investment converter exists.** Every surveyed project is bank-only, parse-only, or abandoned.
- **Banks are killing OFX/Direct Connect.** BofA, Fidelity, AmEx, Truist all discontinued OFX support (2024–2025), forcing millions of users to rely on CSV exports and conversion tools for the first time.
- **Quicken Mac blocks QIF import entirely** — only QFX/OFX works. This makes QIF→OFX essential for ~300K–500K Mac users.
- **Commercial tools are overpriced and stale.** MoneyThumb charges $600–$700 for Pro desktop; ProperConvert is $20/mo subscription for a one-time need; iCreateOFX is $14 but bare-bones. Users resent subscriptions for something they use once.

### Strategy: Open Source First

This is primarily an open-source credibility play, not a SaaS business. Most users need conversion once (switching platforms, backfilling history, bank drops OFX). The plan:

1. **MIT-licensed CLI + Python library on PyPI** — the main product
2. **Optional hosted web version** (free, "buy me a coffee" link)
3. **Mac App Store wrapper** at $9.99 if traction warrants — impulse-buy for non-technical users
4. Investment transaction support is the differentiator that earns stars and forum citations

### Planned Format Support

| Direction | Banking | Investment | Status |
|-----------|---------|------------|--------|
| QIF → QFX | ✅ Done | 🔲 Planned | Banking shipped |
| QFX → QIF | 🔲 Planned | 🔲 Planned | Easy (reverse of above) |
| CSV → QFX | 🔲 Planned | 🔲 Planned | High demand (bank OFX shutdowns) |
| CSV → QIF | 🔲 Planned | 🔲 Planned | |
| QFX → CSV | 🔲 Planned | 🔲 Planned | |
| QIF → CSV | 🔲 Planned | 🔲 Planned | |

### Investment Transaction Architecture

The core challenge is mapping between QIF's ~35 action codes and OFX's 21 transaction types. The mapping is ~85% clean; the remaining 15% involves genuine data loss.

#### QIF Investment Format (`!Type:Invst`)

Fields: D (date), N (action code), Y (security name — NOT ticker), I (price/share), Q (quantity), T (total amount), U (high-precision duplicate of T), C (cleared), P (payee/text), M (memo), O (commission — the ONLY cost field), L (category or `[transfer account]`), $ (transfer amount).

The **X-suffix convention** is critical: actions without X affect the account's own cash balance; X-suffixed actions transfer cash to/from another account in the L field.

**Complete action code inventory:**

*Buy/Sell:* Buy, BuyX, Sell, SellX, ShtSell, CvrShrt

*Income:* Div/DivX, CGLong/CGLongX, CGShort/CGShortX, CGMid/CGMidX (1997 only), IntInc/IntIncX, MiscInc/MiscIncX

*Reinvestment:* ReinvDiv, ReinvLg, ReinvSh, ReinvMd (1997 only), ReinvInt

*Transfers & Other:* ShrsIn, ShrsOut, StkSplit, XIn, XOut, MargInt/MargIntX, MiscExp/MiscExpX, RtrnCap/RtrnCapX, Cash, Deposit

*Retirement:* ContribX, WithdrwX

*Stock Options:* Grant, Vest, Exercise, Expire, Reprice

#### OFX Investment Format (`INVSTMTMSGSRSV1`)

21 transaction types under INVTRANLIST:

*Buy:* BUYSTOCK (BUYTYPE: BUY/BUYTOCOVER), BUYMF, BUYDEBT, BUYOPT (OPTBUYTYPE: BUYTOOPEN/BUYTOCLOSE), BUYOTHER

*Sell:* SELLSTOCK (SELLTYPE: SELL/SELLSHORT), SELLMF, SELLDEBT, SELLOPT (OPTSELLTYPE: SELLTOCLOSE/SELLTOOPEN), SELLOTHER

*Income/Reinvest:* INCOME (INCOMETYPE: DIV/INTEREST/CGLONG/CGSHORT/MISC), REINVEST (same INCOMETYPE enum)

*Other:* TRANSFER, SPLIT, INVBANKTRAN, MARGININTEREST, INVEXPENSE, RETOFCAP, JRNLFUND, JRNLSEC, CLOSUREOPT

OFX separates costs into COMMISSION, FEES, TAXES, LOAD, MARKUP, MARKDOWN — vs QIF's single O field. This is the biggest data loss in OFX→QIF conversion.

OFX identifies securities by CUSIP (9-char alphanumeric) via SECID/UNIQUEID in a separate SECLIST section. QIF uses security name strings only.

#### Key Mapping (QIF → OFX)

| QIF Action | OFX Element | Notes |
|------------|-------------|-------|
| Buy/BuyX | BUYSTOCK (BUY) | X variant generates companion INVBANKTRAN |
| Sell/SellX | SELLSTOCK (SELL) | |
| ShtSell | SELLSTOCK (SELLSHORT) | |
| CvrShrt | BUYSTOCK (BUYTOCOVER) | |
| Div/DivX | INCOME (DIV) | |
| CGLong/CGLongX | INCOME (CGLONG) | |
| CGShort/CGShortX | INCOME (CGSHORT) | |
| IntInc/IntIncX | INCOME (INTEREST) | |
| ReinvDiv | REINVEST (DIV) | |
| ReinvLg/ReinvSh | REINVEST (CGLONG/CGSHORT) | |
| ReinvInt | REINVEST (INTEREST) | |
| ShrsIn/ShrsOut | TRANSFER (IN/OUT) | |
| StkSplit | SPLIT | Q ratio → NUMERATOR/DENOMINATOR |
| MargInt | MARGININTEREST | |
| MiscExp | INVEXPENSE | |
| RtrnCap | RETOFCAP | |
| XIn/XOut | INVBANKTRAN | Wraps standard STMTTRN |

#### Key Data Loss Scenarios

- **OFX→QIF: Fee granularity collapses.** COMMISSION + FEES + TAXES + LOAD all collapse to QIF's single O field.
- **OFX→QIF: Options/bonds lose metadata.** PUT/CALL type, strike price, expiration, shares per contract — all gone. Irrecoverable.
- **QIF→OFX: Must generate SECLIST.** Needs CUSIP lookup (external DB, SEC EDGAR, or user-provided mapping file).
- **QIF→OFX: Must generate FITIDs.** Use deterministic hash of date+action+security+amount+index.
- **Both: Short sales unreliable.** Quicken sometimes exports ShtSell as plain Sell. Moneydance can't import ShtSell/CvrShrt at all.
- **Both: CGMid has no OFX equivalent.** Map to CGSHORT with warning (1997 tax year only).
- **OFX→QIF: JRNLFUND/JRNLSEC have no equivalent.** Approximate with XIn/XOut or ShrsOut/ShrsIn pairs.

### CSV Support Notes

CSV is the most common export format but the most inconsistent — every institution uses different column names, date formats, and transaction type labels. Plan:

- **Brokerage CSVs** (Fidelity, Schwab, Vanguard, E*Trade, IBKR): Each needs a source-specific column mapping. Plugin/config system with YAML or JSON mapping files.
- **Banking CSVs** (Chase, Wells Fargo, BofA, Citi): Simpler — date, description, amount. Auto-detect common formats.
- **PayPal CSV**: Has Transaction ID, Date, Description, Currency, Gross, Fee, Net, Balance, Transaction Type columns.
- **Quicken CSV Mint format**: Quicken Mac accepts this for banking import — Date, Payee, Amount, Tags (4 columns minimum).

### Existing Libraries to Build On

- **ofxtools** (csingley/ofxtools, 325 stars): Parses AND generates OFX 1.6/2.03 with complete investment message set support. No external deps. Best foundation for OFX side.
- **quiffen** (240 weekly PyPI downloads): Parses and writes QIF with investment transaction support. Active project.
- **csv2ofx** (reubano/csv2ofx, 204 stars): CSV→OFX for banking only. Good reference for CSV column mapping patterns.
- **ofxparse** (jseutter/ofxparse, 22K weekly downloads): OFX parser only (no generation). Widely used but not actively maintained.

### Competitive Landscape

| Tool | Price | Investment | Open Source | Notes |
|------|-------|------------|-------------|-------|
| MoneyThumb Pro | $600–$700 | Yes | No | Desktop + OCR. Angry reviews about "lifetime" licenses requiring renewal. |
| ProperConvert | $20/mo or $200 lifetime | Cash only | No | No full investment support. Mac users call it "really steep." |
| iCreateOFX | $14 personal | Separate product | No | Bare-bones. Specific brokerage formats only (TD, Fidelity, Schwab). |
| Big Red Consulting | $69–$79 | No | No | Excel-based. |
| Our tool | Free | Planned | Yes (MIT) | Only open-source option with investment support. |

### Quicken-Specific Gotchas

- **Quicken Mac blocks QIF import** for all ongoing data. Only QFX/OFX works.
- **Quicken Windows** still imports QIF for investment accounts (banking QIF restricted since 2005, workarounds exist).
- **QIF date format landmine:** US = MM/DD; Australian = DD/MM. Post-2000 Windows uses apostrophe: `01/15'07`. Two-digit year `01/15/24` = **1924**, not 2024. Always generate 4-digit years.
- **QIF encodes securities by name** (exact match required). **QFX uses CUSIP** (9-char identifier). Mismatch = Quicken creates duplicate security.
- **Quicken stores imported FITIDs permanently** — even for deleted transactions. Re-importing same FITIDs = silently skipped. Deterministic FITID generation is essential.
- **Quicken Simplifi** accepts only CSV imports (4-field minimum: Date, Payee, Amount, Tags). No QFX import. No migration path from Classic.
- **32-character payee limit** in QFX — truncate longer names.
- **ANSI encoding required** — Quicken Windows rejects UTF-8 QIF files.
