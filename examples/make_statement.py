#!/usr/bin/env python3
"""SAMPLE STATEMENT, FICTIONAL PERSON. Deterministic September 2026 example.

One annotated data table drives CSV, HTML, and the private test answer key.
PDF conversion is optional: python3 examples/make_statement.py --pdf
No packages, accounts, downloads or remote services.
"""
import argparse
import calendar
import csv
from datetime import date
from decimal import Decimal
from html import escape
import json
from pathlib import Path
import random
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'examples'
NOTICE = 'SAMPLE STATEMENT, FICTIONAL PERSON'
BANK = 'Cedar Kite Bank (fictional)'
PERSON = 'Alex Mercer (fictional), age 27, Raleigh, NC'
OPENING = Decimal('295.00')
SEED = 202609


def table():
    rows = []
    def add(day, description, amount, category, *tags):
        rows.append({'date': f'2026-09-{day:02}', 'description': description,
                     'amount': Decimal(amount), 'category': category, 'tags': list(tags)})
    # All amounts are invented except the sourced, named subscription list below.
    for day in (4, 18):
        add(day, 'CEDAR LANE DESIGN PAYROLL DIRECT DEP', '1640.00', 'Income')
    for day, description, amount, category in [
        (5, 'OAK COURT APTS RENT ACH', '-975.00', 'Housing'),
        (20, 'AUTO LOAN PAYMENT', '-259.00', 'Car Payment'),
        (21, 'AUTO INSURANCE ACH', '-123.45', 'Insurance'),
        (22, 'ELECTRIC UTILITY BILLPAY', '-92.18', 'Utilities'),
        (24, 'MOBILE PHONE AUTOPAY', '-55.00', 'Phone & Internet'),
        (25, 'HOME INTERNET AUTOPAY', '-65.00', 'Phone & Internet'),
        (19, 'STUDENT LOAN ACH', '-125.00', 'Debt Payments'),
        (6, 'VENMO CASHOUT ROOMMATE UTILITIES', '60.00', 'Transfers'),
    ]:
        add(day, description, amount, category)
    subscriptions = [
        (2, 'NETFLIX.COM', '19.99', 'Netflix Standard', ''),
        (3, 'HULU', '11.99', 'Hulu with ads', 'hulu_overlap'),
        (3, 'DISNEY PLUS BUNDLE', '12.99', 'Disney+ and Hulu with ads', ''),
        (6, 'SPOTIFY USA', '12.99', 'Spotify Individual', 'music_overlap'),
        (7, 'GOOGLE *YOUTUBE PREMIUM', '15.99', 'YouTube Premium Individual', ''),
        (11, 'APPLE.COM/BILL', '2.99', 'iCloud+ 200 GB (hidden behind Apple billing)', ''),
        (13, 'AMAZON PRIME', '14.99', 'Amazon Prime monthly', ''),
        (14, 'PLANET FITNESS', '15.00', 'Planet Fitness Classic', ''),
        (15, 'DOORDASH DASHPASS', '9.99', 'DashPass monthly', ''),
        (16, 'UBER ONE', '9.99', 'Uber One monthly', 'delivery_pass'),
        (17, 'AUDIBLE MEMBERSHIP', '14.95', 'Audible Premium Plus', 'unused_audible'),
        (20, 'OPENAI *CHATGPT PLUS', '20.00', 'ChatGPT Plus', ''),
        (23, 'PARAMOUNT+', '8.99', 'Paramount+ Essential, promotional trial expired', 'trial'),
    ]
    for day, merchant, amount, name, tag in subscriptions:
        add(day, merchant, '-' + amount, 'Health & Fitness' if 'FITNESS' in merchant else 'Subscriptions',
            'recurring', *([tag] if tag else []))
        rows[-1]['subscription'] = name
    rng = random.Random(SEED)
    for day in range(1, 31):
        if date(2026, 9, day).weekday() < 5:
            # Distinct cents keep the deliberately planted duplicate unambiguous.
            add(day, f'POS DEBIT STARBUCKS #1042 RALEIGH NC 09/{day:02}',
                '-' + str(Decimal(450 + day*3) / 100), 'Restaurants & Coffee', 'coffee')
    delivery_days = [2, 4, 5, 6, 8, 10, 11, 13, 15, 16, 18, 20, 21, 23, 25, 27, 28, 30]
    for i, day in enumerate(delivery_days):
        merchant = 'DOORDASH*' + ['CHIPOTLE', 'CAVA', 'WINGSTOP'][i % 3] if i % 2 == 0 else 'UBER *EATS'
        amount = Decimal(rng.randint(2600, 4250)) / 100
        add(day, merchant, '-' + str(amount), 'Delivery & Takeout', 'delivery')
    for day, amount, merchant in [(4, '78.43', 'ALDI'), (9, '62.18', 'FOOD LION'),
                                  (14, '54.72', 'TRADER JOES'), (18, '84.16', 'ALDI'),
                                  (24, '49.88', 'FOOD LION'), (29, '38.91', 'ALDI')]:
        add(day, f'POS DEBIT {merchant} #0284 RALEIGH NC', '-' + amount, 'Groceries')
    for day, amount in [(5, '36.17'), (16, '39.42'), (25, '34.08')]:
        add(day, 'POS DEBIT SHELL #0328 RALEIGH NC', '-' + amount, 'Gas & Transit')
    for day, amount in [(6, '42.18'), (11, '67.49'), (17, '23.99'), (22, '78.14'), (26, '57.86')]:
        add(day, f'AMZN MKTP US*Q{day:02}X', '-' + amount, 'Shopping')
    for _ in range(2):
        add(18, 'TARGET #1182 RALEIGH NC', '-28.74', 'Shopping', 'double_charge')
    for day, amount, description, category in [
        (12, '26.81', 'TST* NOODLE HOUSE RALEIGH NC', 'Restaurants & Coffee'),
        (21, '31.64', 'TST* BURGER BAR RALEIGH NC', 'Restaurants & Coffee'),
        (26, '24.16', 'SQ * TACO SHOP RALEIGH NC', 'Restaurants & Coffee'),
        (14, '19.50', 'MOVIE THEATER', 'Entertainment'),
        (26, '25.00', 'BOWLING NIGHT', 'Entertainment'),
        (22, '32.00', 'SQ * OAK BARBER RALEIGH NC', 'Personal Care'),
        (20, '18.90', 'UBER *TRIP', 'Rideshare'),
        (27, '22.60', 'UBER *TRIP', 'Rideshare'),
    ]:
        add(day, description, '-' + amount, category)
    for day in (12, 24):
        add(day, 'ATM CASH WITHDRAWAL RALEIGH NC', '-40.00', 'Cash & ATM')
        add(day, 'NON-NETWORK ATM FEE', '-3.00', 'Bank Fees & Interest', 'fee')
        add(day, 'ATM OPERATOR FEE', '-3.50', 'Bank Fees & Interest', 'fee')
    # The returned payment reverses; only the NSF fee remains an expense.
    add(28, 'ONLINE PAYMENT ATTEMPT', '-85.00', 'Other')
    add(28, 'ONLINE PAYMENT REVERSAL', '85.00', 'Other')
    add(29, 'OVERDRAFT FEE', '-35.00', 'Bank Fees & Interest', 'fee')
    add(29, 'INSUFFICIENT FUNDS NSF RETURNED ITEM FEE', '-30.00', 'Bank Fees & Interest', 'fee')
    add(30, 'MONTHLY MAINTENANCE FEE', '-12.00', 'Bank Fees & Interest', 'fee')
    return sorted(rows, key=lambda r: r['date'])


def encode(value):
    if isinstance(value, Decimal):
        return format(value, '.2f')
    raise TypeError(type(value).__name__)


def generate():
    rows = table()
    balance = OPENING
    deposits = sum((r['amount'] for r in rows if r['amount'] > 0), Decimal('0'))
    withdrawals = -sum((r['amount'] for r in rows if r['amount'] < 0), Decimal('0'))
    fees = -sum((r['amount'] for r in rows if 'fee' in r['tags']), Decimal('0'))
    # Metadata before the header deliberately exercises real bank export preambles.
    preamble = [[NOTICE], [BANK], ['Account', '****4417'],
                ['Beginning balance as of 09/01/2026', '', format(OPENING, '.2f')],
                ['Total credits', '', format(deposits, '.2f')],
                ['Total debits', '', format(-withdrawals, '.2f')],
                ['Ending balance as of 09/30/2026', '', format(OPENING+deposits-withdrawals, '.2f')], []]
    with (OUT / 'statement-2026-09.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerows(preamble)
        writer.writerow(['Date', 'Description', 'Amount', 'Running Bal.'])
        for i, row in enumerate(rows, len(preamble)+2):
            balance += row['amount']
            row.update(balance=balance, source_row=i, id=f'S1:{i}')
            writer.writerow([date.fromisoformat(row['date']).strftime('%m/%d/%Y'), row['description'],
                             format(row['amount'], '.2f'), format(balance, '.2f')])
    summary = {'opening': OPENING, 'deposits': deposits, 'withdrawals': withdrawals,
               'fees_included_in_withdrawals': fees, 'closing': balance, 'count': len(rows)}
    sums = {}
    for row in rows:
        c = row['category']
        sums[c] = sums.get(c, Decimal('0')) + (row['amount'] if c == 'Income' else -row['amount'])
    income = sums['Income']
    spending = sum((v for c, v in sums.items() if c not in ('Income', 'Transfers', 'Savings')), Decimal('0'))
    def tagged(tag):
        chosen = [r for r in rows if tag in r['tags']]
        return {'lines': [r['id'] for r in chosen], 'count': len(chosen),
                'monthly': -sum((r['amount'] for r in chosen), Decimal('0'))}
    planted = {tag: tagged(tag) for tag in ['hulu_overlap', 'music_overlap', 'delivery_pass',
                'unused_audible', 'trial', 'double_charge', 'fee', 'delivery', 'coffee', 'recurring']}
    planted['double_charge']['monthly'] = Decimal('28.74')  # one extra charge, not both
    planted['trial']['note'] = 'Fictional backstory only. A statement cannot prove a trial expired.'
    planted['unused_audible']['note'] = 'Fictional backstory only. A statement cannot prove usage.'
    key = {'notice': NOTICE, 'person': PERSON, 'bank': BANK, 'summary': summary,
           'income': income, 'spending': spending, 'categories': sums, 'planted_leaks': planted,
           'transactions': rows}
    (ROOT / 'tests' / 'fixtures').mkdir(parents=True, exist_ok=True)
    (ROOT / 'tests/fixtures/answer-key.json').write_text(json.dumps(key, default=encode, indent=2) + '\n')
    table_rows = ''.join('<tr><td>' + date.fromisoformat(r['date']).strftime('%m/%d/%Y') + '</td><td>'
                        + escape(r['description']) + '</td><td class="money">' + format(r['amount'], '.2f')
                        + '</td><td class="money">' + format(r['balance'], '.2f') + '</td></tr>' for r in rows)
    summary_rows = ''.join('<tr><td>' + label + '</td><td class="money">' + ('-' if summary[key] < 0 else '') + '$' + format(abs(summary[key]), ',.2f')
                          + '</td></tr>' for key, label in [('opening', 'Opening balance'), ('deposits', 'Deposits / credits'),
                              ('withdrawals', 'Withdrawals / debits'), ('fees_included_in_withdrawals', 'Fees (already in withdrawals)'), ('closing', 'Closing balance')])
    html = '''<!doctype html>
<!-- SAMPLE STATEMENT, FICTIONAL PERSON -->
<html lang="en"><head><meta charset="utf-8"><title>Fictional September statement</title>
<style>
@page { size: letter; margin: 0.55in; }
body {font: 10pt Arial, sans-serif; color: #243247;}
h1 {font-size: 24pt; margin-bottom: 6pt;} h2 {font-size: 14pt; margin: 16pt 0 8pt;}
.notice {font-size: 11pt; font-weight: bold; color: #7d341d;}
.meta {line-height: 1.5;} table {width: 100%; border-collapse: collapse;}
.summary {width: 65%; margin-bottom: 16pt;}
td, th {padding: 6pt 5pt; border-bottom: 1px solid #dde3e8; text-align: left;}
th {background: #243247; color: white; font-size: 9pt;}
.money {text-align: right; white-space: nowrap;} .transactions td {font-size: 8.5pt;}
thead {display: table-header-group;} tr {page-break-inside: avoid;}
.footer {font-size: 8pt; margin-top: 12pt;}
</style></head><body>
'''
    html += f'<p class="notice">{NOTICE}</p><h1>{BANK}</h1><p class="meta">{PERSON}<br>Everyday checking | Account ****4417<br>September 1-30, 2026 | USD</p>'
    html += '<h2>Account summary</h2><table class="summary">' + summary_rows + '</table>'
    html += f'<h2>Every transaction ({len(rows)})</h2><table class="transactions"><thead><tr><th>Date</th><th>Description</th><th>Amount ($)</th><th>Balance ($)</th></tr></thead><tbody>' + table_rows + '</tbody></table>'
    html += '<p class="footer">SAMPLE STATEMENT, FICTIONAL PERSON. This bank, person and account are invented. Charges and dates are examples, not financial records. A reversed payment is shown as a debit and a credit. Fees appear separately.</p></body></html>\n'
    (OUT / 'statement-2026-09.html').write_text(html, encoding='utf-8')
    return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', action='store_true')
    args = parser.parse_args()
    key = generate()
    print(json.dumps({'notice': NOTICE, **key['summary'], 'income': key['income'], 'spending': key['spending']}, default=encode, indent=2))
    if args.pdf:
        binary = shutil.which('soffice')
        if not binary:
            print('PDF not created: soffice is not on PATH. HTML is ready to print.')
            return
        profile = ROOT / 'tmp' / 'libreoffice-example'
        profile.parent.mkdir(parents=True, exist_ok=True)
        command = [binary, '-env:UserInstallation=' + profile.as_uri(), '--headless', '--convert-to', 'pdf',
                   '--outdir', str(OUT), str(OUT / 'statement-2026-09.html')]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        print(result.stdout.strip())
        if result.returncode or not (OUT / 'statement-2026-09.pdf').exists():
            print(f'PDF conversion failed (exit {result.returncode}): ' + result.stderr.strip() + '. HTML is ready to print.')


if __name__ == '__main__':
    main()
