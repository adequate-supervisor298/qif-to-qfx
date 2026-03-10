#!/usr/bin/env python3
"""
QIF → Clean QFX Converter for Quicken Mac Import

Solves common problems with QIF exports from financial services (PayPal,
Venmo, banks, etc.) that make them unusable for direct Quicken Mac import:

1. SPLITS: Strips $0 "Fee" split lines that cause Quicken to show "Split"
2. BALANCE: Optionally generates offsetting entries so the file nets to zero
3. HEADER: Adds missing !Account header block if absent
4. FORMAT: Outputs QFX (Web Connect) so Quicken can import into existing accounts

Usage:
    python3 qif_to_qfx.py input.qif [output.qfx] [--no-balance] [--org NAME]

Options:
    --no-balance    Skip auto-balancing (use if source already balances to zero)
    --org NAME      Set the institution name in the QFX header (default: Import)
    --acctid ID     Set the account identifier (default: Import). Use a unique
                    value per source to prevent Quicken from mixing accounts.

If output is omitted, writes to input-clean.qfx in the same directory.
"""

import sys
import os
import hashlib
from datetime import datetime


# ── QIF Parsing ──────────────────────────────────────────────────────────────

def ensure_account_header(content):
    """Ensure QIF file has an account header block.
    Some QIF exports omit this, but Quicken needs it for import."""
    if content.lstrip().startswith("!Account"):
        return content
    header = "!Account\nNImport\nTCash\n^\n"
    print("  Added missing !Account header")
    return header + content


def parse_qif(filepath):
    """Parse a QIF file into a list of transaction dicts.
    Automatically strips split lines (S/$ prefixed)."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    content = ensure_account_header(content)

    blocks = content.split("^\n")
    txns = []

    for block in blocks:
        lines = block.strip().split("\n")
        t = {}
        for line in lines:
            if not line:
                continue
            code, val = line[0], line[1:]
            if code == "D":
                t["date"] = val
            elif code == "T":
                try:
                    t["amount"] = float(val.replace(",", ""))
                except ValueError:
                    pass
            elif code == "L":
                t["category"] = val
            elif code == "P":
                t["payee"] = val
            elif code == "M":
                t["memo"] = val
            # S and $ lines (splits) are silently skipped
        if "amount" in t and "date" in t:
            txns.append(t)

    return txns


# ── Balancing ────────────────────────────────────────────────────────────────

def balance_transactions(txns):
    """Add offsetting entries so the file nets to zero.

    Some QIF exports (especially PayPal) are inconsistent about including
    both sides of each transaction. This matches debits to credits by
    date+amount, then generates balancing entries for anything unmatched."""
    debits = [(i, t) for i, t in enumerate(txns) if t["amount"] < 0]
    credits = [(i, t) for i, t in enumerate(txns) if t["amount"] > 0]

    used_credits = set()
    unmatched_debits = []

    for _, d in debits:
        matched = False
        for j, (ci, c) in enumerate(credits):
            if ci in used_credits:
                continue
            if d.get("date") == c.get("date") and abs(d["amount"] + c["amount"]) < 0.01:
                used_credits.add(ci)
                matched = True
                break
        if not matched:
            unmatched_debits.append(d)

    unmatched_credits = [c for ci, c in credits if ci not in used_credits]

    generated = []
    for d in unmatched_debits:
        generated.append({
            "date": d["date"],
            "amount": abs(d["amount"]),
            "category": "General Card Deposit",
            "payee": "",
            "memo": d.get("memo", ""),
        })
    for c in unmatched_credits:
        generated.append({
            "date": c["date"],
            "amount": -c["amount"],
            "category": "General Card Withdrawal",
            "payee": "",
            "memo": c.get("memo", ""),
        })

    return txns + generated


# ── QFX Output ───────────────────────────────────────────────────────────────

def date_to_ofx(date_str):
    """Convert MM/DD/YYYY to YYYYMMDD."""
    parts = date_str.split("/")
    if len(parts) == 3:
        mm, dd, yy = parts
        if len(yy) == 2:
            yy = "20" + yy if int(yy) < 50 else "19" + yy
        return f"{yy}{mm.zfill(2)}{dd.zfill(2)}"
    return date_str


def make_fitid(txn, index):
    """Generate a unique, deterministic FITID for dedup across imports."""
    raw = f"{txn['date']}|{txn['amount']:.2f}|{txn.get('payee', '')}|{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:24]


def escape_ofx(s):
    """Escape special characters for OFX/SGML."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_qfx(txns, filepath, account_id="Import", org="Import"):
    """Write transactions as a Quicken-compatible QFX file.

    Uses INTU.BID 10898 (Chase) which is a known-working Web Connect
    partner. On import, Quicken will ask which account to link to."""
    ofx_dates = [date_to_ofx(t["date"]) for t in txns]
    dt_start = min(ofx_dates)
    dt_end = max(ofx_dates)
    dt_server = datetime.now().strftime("%Y%m%d%H%M%S")
    balance = sum(t["amount"] for t in txns)

    trn_lines = []
    for i, t in enumerate(txns):
        payee = escape_ofx(t.get("payee", "").strip() or t.get("category", "Unknown"))
        memo = escape_ofx(t.get("memo", "").strip())
        fitid = make_fitid(t, i)
        ofx_date = date_to_ofx(t["date"])
        ttype = "CREDIT" if t["amount"] > 0 else "DEBIT"

        trn = f"""<STMTTRN>
<TRNTYPE>{ttype}
<DTPOSTED>{ofx_date}
<TRNAMT>{t['amount']:.2f}
<FITID>{fitid}
<n>{payee[:32]}"""
        if memo:
            trn += f"\n<MEMO>{memo[:255]}"
        trn += "\n</STMTTRN>"
        trn_lines.append(trn)

    qfx = f"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>{dt_server}
<LANGUAGE>ENG
<FI>
<ORG>{org}
<FID>10898
</FI>
<INTU.BID>10898
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>0
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>USD
<BANKACCTFROM>
<BANKID>10898
<ACCTID>{account_id}
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>{dt_start}000000
<DTEND>{dt_end}235959
{chr(10).join(trn_lines)}
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>{balance:.2f}
<DTASOF>{dt_end}235959
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(qfx)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Parse args (simple, no argparse dependency)
    args = sys.argv[1:]
    no_balance = "--no-balance" in args
    if no_balance:
        args.remove("--no-balance")

    org = "Import"
    if "--org" in args:
        idx = args.index("--org")
        org = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    acctid = "Import"
    if "--acctid" in args:
        idx = args.index("--acctid")
        acctid = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if len(args) < 1:
        print("Usage: python3 qif_to_qfx.py input.qif [output.qfx] [--no-balance] [--org NAME] [--acctid ID]")
        sys.exit(1)

    input_path = args[0]
    if len(args) >= 2:
        output_path = args[1]
    else:
        base = os.path.splitext(input_path)[0]
        output_path = base + "-clean.qfx"

    print(f"Reading: {input_path}")
    txns = parse_qif(input_path)
    print(f"  Parsed: {len(txns)} transactions (splits stripped)")

    dates = sorted(t["date"] for t in txns)
    print(f"  Date range: {dates[0]} – {dates[-1]}")

    debits = sum(t["amount"] for t in txns if t["amount"] < 0)
    credits = sum(t["amount"] for t in txns if t["amount"] > 0)
    net = debits + credits
    print(f"  Debits: ${debits:,.2f}  Credits: ${credits:,.2f}  Net: ${net:,.2f}")

    if no_balance:
        balanced = txns
        print(f"  Balancing: skipped (--no-balance)")
    elif abs(net) < 0.01:
        balanced = txns
        print(f"  Balancing: not needed (already $0.00)")
    else:
        balanced = balance_transactions(txns)
        generated = len(balanced) - len(txns)
        final_net = sum(t["amount"] for t in balanced)
        print(f"  Balancing entries added: {generated}")
        print(f"  Final net: ${final_net:,.2f}")

    write_qfx(balanced, output_path, account_id=acctid, org=org)
    print(f"\nWritten: {output_path}")
    print(f"  Total transactions: {len(balanced)}")
    print(f"\nImport: File → Import → Web Connect (.QFX) → Link to existing account")


if __name__ == "__main__":
    main()
