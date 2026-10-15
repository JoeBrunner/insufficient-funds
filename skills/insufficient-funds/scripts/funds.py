#!/usr/bin/env python3
"""Statement arithmetic, Python 3.9+, standard library only.

PLAN JSON (money as quoted decimal strings; no guessed totals):
{
  "targets": {"Income": {"amount": "3200.00", "why": "Observed paychecks"},
              "Housing": {"amount": "1000.00", "why": "Rent unchanged"},
              "...every category in categories.md...": {"amount": "0.00", "why": "Unused"}},
  "buffer": "100.00",
  "buffer_goal": "500.00",
  "buffer_current": "0.00",
  "leaks": [{"what": "Hulu already included in bundle, check both plans",
             "lines": ["S1:12"], "share": "1", "kind": "recurring",
             "action": "Cancel standalone Hulu if bundle confirmed",
             "where": "Hulu > Account > Cancel"}],
  "assumptions": ["Keep the bundle; cancel standalone Hulu if included."]
}
With income: one target for EVERY category. Transfers target must be zero. Savings target
includes buffer. All non-Income/Transfers targets sum to observed Income.
Fixed categories cannot change. Every cut needs a reason; used flexible lines
stay positive and at least half of last month. A full budget always funds Entertainment.
Buffer receives savings first, up to buffer_goal minus buffer_current.
Without income: omit Income/Savings targets and all buffer fields. Total spending
targets must not exceed observed spending. To fund this later, add the person's
take_home_pay, Income/Savings targets and buffer fields; never count card payments.
Habit leaks are automatic half cuts (rounded DOWN to cents). Do not put them in
plan.leaks or choose their shares. Other leak share is 0..1 of referenced outflows. Code computes monthly = sum * share,
yearly = monthly * 12, except check items have NO yearly value.
A double-charge check is one EXTRA charge, even when both lines are referenced.
kind: recurring, observed, check. Observed means this
month's pattern repeated, NOT a forecast. Checks are excluded from leak totals
and must not fund a budget (e.g. an unconfirmed double charge).
Run analyze --month YYYY-MM for multi-month history; budget uses that month.
Categories JSON: {"MERCHANT KEY": {"category": "Groceries", "name": "Aldi"}}.
For every subscription/membership, add where (cancel route), billing (monthly,
yearly, unclear), and kind: video, music, cloud storage, delivery pass, fitness,
AI, news, shopping membership, software, other. No default monthly assumption.
Over $60 per charge needs billing unclear or a billing_reason confirming monthly.
Yearly charges are divided by 12, labeled; unclear charges have no annual estimate.
The headline counts monthly-billed services only; yearly equivalents are separate.
Use plan.fee_actions = {"interest": {"action": "Review the payoff amount"}} for EVERY
fee_leaks ID from analyze. Code adds the rows. Non-interest fees default to observed;
set kind: check when avoidance is uncertain. Interest is always check, never savings.
Do not repeat fee lines in leaks. Overlap reviews are mandatory: a leak row has
"overlap": "music", "keep": "YOUTUBE PREMIUM" (exact merchant key), and all canceled
services' lines; or kind: check, every overlap line, and a one-line reason.
Amazon Prime counts as video too; Disney bundles and standalone Hulu get a bundle
check. Unclear and yearly billing use check rows; do not assume those charges repeat next month.
"""
import argparse
import calendar
import csv
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import sys

ZERO = Decimal('0.00')
CENT = Decimal('0.01')
UNVERIFIED_NOTICE = ("Your file has no balances to check against, so these totals come from the file itself. "
    "Paste the summary box from your statement (previous balance, payments, purchases, fees, "
    "interest, new balance) and I'll check every line against it.")
SUBSCRIPTION_KINDS = ('video', 'music', 'cloud storage', 'delivery pass', 'fitness',
                      'AI', 'news', 'shopping membership', 'software', 'other')
BILLING = ('monthly', 'yearly', 'unclear')
CATEGORIES = (
    'Income', 'Housing', 'Utilities', 'Phone & Internet', 'Insurance', 'Car Payment',
    'Gas & Transit', 'Rideshare', 'Groceries', 'Delivery & Takeout', 'Restaurants & Coffee',
    'Subscriptions', 'Shopping', 'Health & Fitness', 'Personal Care', 'Entertainment',
    'Travel', 'Kids & Pets', 'Gifts & Giving', 'Debt Payments', 'Bank Fees & Interest',
    'Cash & ATM', 'Transfers', 'Savings', 'Other')
FIXED = {'Housing', 'Utilities', 'Phone & Internet', 'Insurance', 'Car Payment',
         'Health & Fitness', 'Kids & Pets', 'Debt Payments'}
FLEXIBLE = set(CATEGORIES) - FIXED - {'Income', 'Transfers', 'Savings',
                                    'Subscriptions', 'Bank Fees & Interest'}
FIELDS = ('id', 'date', 'description', 'amount', 'balance', 'source_file', 'source_row')
ALIASES = {
    'date': ['postingdate', 'posteddate', 'postdate', 'date', 'transactiondate'],
    'description': ['description', 'transactiondescription', 'payee', 'merchant', 'memo'],
    'amount': ['amount', 'transactionamount'],
    'debit': ['debit', 'debits', 'withdrawal', 'withdrawals', 'debitamount'],
    'credit': ['credit', 'credits', 'deposit', 'deposits', 'creditamount'],
    'type': ['debitcredit', 'transactiontype', 'type'],
    'balance': ['runningbalance', 'runningbal', 'balance', 'availablebalance']}
FEE = re.compile(r'\b(?:OVERDRAFT|NSF|INSUFFICIENT FUNDS|RETURNED (?:ITEM|PAYMENT)|'
                 r'(?:ATM|ATM OPERATOR|NON.?BANK ATM|NON.?NETWORK ATM).*FEE|'
                 r'MONTHLY (?:MAINTENANCE|SERVICE)|FOREIGN TRANSACTION|LATE (?:FEE|PAYMENT FEE)|'
                 r'INTEREST (?:CHARGE|CHARGED)|PURCHASE INTEREST|FINANCE CHARGE)\b', re.I)
SUBSCRIPTION = re.compile(r'NETFLIX|HULU|DISNEY|SPOTIFY|YOUTUBE.*PREMIUM|'
                         r'APPLE.COM/BILL|ICLOUD|AMAZON PRIME|AMZN.*PRIME|'
                         r'DASHPASS|UBER.?ONE|AUDIBLE|CHATGPT|OPENAI|'
                         r'PARAMOUNT|PLANET FITNESS|DROPBOX|GOOGLE.*ONE', re.I)


def money(value, blank=True):
    if isinstance(value, (float, bool)):
        raise ValueError('Use decimal strings for money, not floats or booleans')
    s = str(value).strip()
    if not s and blank:
        return ZERO
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    negative = s.startswith('(') and s.endswith(')') or s.endswith('-')
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1]
    if s.endswith('-'):
        s = s[:-1]
    if not re.fullmatch(r'[+-]?\d+(?:\.\d{1,2})?', s):
        raise ValueError('Invalid money value (use dollars and cents)')
    result = Decimal(s)
    if negative:
        result = -abs(result)
    return result.quantize(CENT)


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def dollars(value):
    return f'${value:,.2f}'


def parse_date(value):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError('Unrecognized date; use MM/DD/YYYY, M/D/YY or YYYY-MM-DD')


def safe_text(value):
    """Remove full account/card identifiers before any derived output."""
    value = str(value)
    value = re.sub(r'\b(?:account|acct|card)(?:\s*(?:number|no\.?|ending|#))?\s*[:#-]?\s*([\d -]{5,}\d)',
                   lambda m: 'account ****' + re.sub(r'\D', '', m.group(1))[-4:], value, flags=re.I)
    value = re.sub(r'(?<!\d)(?:\d[ -]?){7,18}\d(?!\d)',
                   lambda m: '****' + re.sub(r'\D', '', m.group())[-4:], value)
    value = re.sub(r'\b\d{5,}\b', '[number removed]', value)
    return value


def clean_json(value):
    if isinstance(value, Decimal):
        return format(value, '.2f')
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    return value


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(value), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + safe_text(key))
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique)


def norm_header(value):
    return re.sub(r'[^a-z]', '', value.lower())


def columns(headers, mapping):
    normalized = [norm_header(h) for h in headers]
    if len(set(normalized)) != len(normalized):
        raise ValueError('Duplicate or ambiguous headers: ' + safe_text(', '.join(headers)))
    found = {}
    for role, choices in ALIASES.items():
        if role in mapping:
            matches = [i for i, h in enumerate(headers) if h.strip().lower() == mapping[role].lower()]
            if not matches:
                raise ValueError('Mapped column missing: ' + safe_text(mapping[role]))
            found[role] = matches[0]
        else:
            hits = [normalized.index(c) for c in choices if c in normalized]
            # Date aliases have an explicit posting-date priority. Other roles must be unique.
            if len(hits) > 1 and role not in ('date', 'description'):
                raise ValueError('Ambiguous ' + role + '; use --map. Headers: ' + safe_text(', '.join(headers)))
            if hits:
                found[role] = hits[0]
    if not ('date' in found and 'description' in found
            and ('amount' in found or {'debit', 'credit'} <= found.keys())):
        raise ValueError('Cannot identify columns. Headers: ' + safe_text(', '.join(headers)) + '; use --map')
    if 'amount' in found and ('debit' in found or 'credit' in found):
        if 'amount' in mapping:
            found.pop('debit', None)
            found.pop('credit', None)
        elif 'debit' in mapping and 'credit' in mapping:
            found.pop('amount')
        else:
            raise ValueError('Both amount and debit/credit found; choose with --map')
    return found


def parse_map(value):
    if not value:
        return {}
    mapping = {}
    for item in next(csv.reader([value])):
        if '=' not in item:
            raise ValueError('--map needs role=column pairs')
        key, col = item.split('=', 1)
        if key not in ALIASES or key in mapping:
            raise ValueError('Unknown or duplicate mapping role: ' + key)
        mapping[key] = col.strip()
    return mapping


def normalize(inputs, output, mapping=None, card=False):
    output = Path(output)
    if output.resolve() in [Path(p).resolve() for p in inputs]:
        raise ValueError('Output must differ from each source statement')
    hashes = [fingerprint(p) for p in inputs]
    if len(set(hashes)) != len(hashes):
        raise ValueError('The same statement was supplied more than once; remove the repeated input')
    mapping = mapping or {}
    records, reports = [], []
    for source_no, filename in enumerate(inputs, 1):
        source = f'S{source_no}'
        with Path(filename).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream)
            raw = []
            previous = 0
            for row in reader:
                raw.append((previous + 1, row))
                previous = reader.line_num
        header_index = None
        errors = []
        for i, (_, row) in enumerate(raw[:100]):
            if not row:
                continue
            try:
                found = columns(row, mapping)
                header_index = i
                break
            except ValueError as exc:
                if any(norm_header(h) in ALIASES['date'] for h in row) or mapping:
                    errors.append(str(exc))
        if header_index is None:
            raise ValueError(errors[-1] if errors else 'Cannot find a transaction header; use --map. Headers: '
                             + safe_text(' | '.join(', '.join(r) for _, r in raw[:6])))
        headers = raw[header_index][1]
        keys = set(norm_header(h) for h in headers)
        amex = {'extendeddetails', 'appears on your statement as'.replace(' ', '')} & keys
        invert = card or bool(amex)
        mode = 'separate debit/credit (debits negative)' if 'debit' in found else (
            'positive purchases inverted (--card or Amex layout)' if invert else 'signed amount (negative is spending)')
        source_records = []
        for line_no, row in raw[header_index + 1:]:
            if not row or not any(c.strip() for c in row):
                continue
            if row == headers:
                continue
            first = next((c.strip() for c in row if c.strip()), '')
            try:
                parse_date(row[found['date']])
                dated = True
            except (ValueError, IndexError):
                dated = False
            if not dated and re.match(r'^(?:total(?: (?:credits|debits|deposits|withdrawals|transactions))?(?:$|:)|'
                        r'beginning balance|ending balance|opening balance|closing balance|'
                        r'account summary|end of (?:statement|transactions)|sample statement)', first, re.I):
                continue
            if len(row) < max(found.values()) + 1:
                raise ValueError(f'{source}:{line_no}: incomplete row; no transaction was silently skipped')
            try:
                when = parse_date(row[found['date']])
                description = safe_text(row[found['description']].strip())
                if not description:
                    raise ValueError('Blank description')
                if description[:1] in ('=', '+', '-', '@'):
                    description = "'" + description
                if 'debit' in found:
                    debit, credit = money(row[found['debit']]), money(row[found['credit']])
                    if debit and credit:
                        raise ValueError('Both debit and credit populated; split or verify this row')
                    amount = abs(credit) - abs(debit)
                else:
                    amount = money(row[found['amount']])
                    direction = row[found['type']].strip().upper() if 'type' in found else ''
                    # Chase checking Details carries CREDIT/DEBIT; Type carries ACH_DEBIT, etc.
                    if 'details' in keys:
                        detail = row[[norm_header(h) for h in headers].index('details')].strip().upper()
                        if detail in ('CREDIT', 'DEBIT'):
                            direction = detail
                    if direction in ('DEBIT', 'D', 'DR', 'SALE', 'PURCHASE', 'WITHDRAWAL', 'FEE', 'CHARGE',
                                     'ACH_DEBIT', 'ATM', 'CHECK', 'DIRECT DEBIT', 'DEBIT CARD'):
                        amount = -abs(amount)
                        mode += '' if 'type-directed' in mode else '; type-directed signs'
                    elif direction in ('CREDIT', 'C', 'CR', 'DEPOSIT', 'RETURN', 'REFUND', 'ACH_CREDIT', 'DIRECT DEP'):
                        amount = abs(amount)
                        mode += '' if 'type-directed' in mode else '; type-directed signs'
                    elif direction == 'PAYMENT':
                        # A checking bill payment is an outflow; a card payment is a credit.
                        # Preserve signed amounts unless --card/Amex explicitly sets the convention.
                        amount = -amount if invert else amount
                    elif direction:
                        raise ValueError('Unknown direction in Type column; verify and transcribe to signed CSV')
                    elif invert:
                        amount = -amount
                balance_text = row[found['balance']].strip() if 'balance' in found else ''
                balance = money(balance_text) if balance_text else None
                source_records.append(dict(id=f'{source}:{line_no}', date=when, description=description,
                    amount=amount, balance=balance, source_file=source, source_row=line_no))
            except ValueError as exc:
                raise ValueError(f'{source}:{line_no}: {exc}') from exc
        if not source_records:
            raise ValueError(source + ': no transactions found')
        records.extend(source_records)
        reports.append({'source': source, 'columns': {k: safe_text(headers[v]) for k, v in found.items()},
                        'signs': mode, **totals(source_records)})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        for row in records:
            writer.writerow({k: ('' if v is None else format(v, '.2f') if isinstance(v, Decimal) else v)
                             for k, v in row.items()})
    return reports


def read_transactions(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(FIELDS) <= set(reader.fieldnames):
            raise ValueError('Use normalize first; normalized columns are missing')
        records = list(reader)
    seen = set()
    for row in records:
        if row['id'] in seen:
            raise ValueError('Duplicate transaction ID: ' + row['id'])
        seen.add(row['id'])
        row['date'] = parse_date(row['date'])
        row['amount'] = money(row['amount'], blank=False)
        row['balance'] = money(row['balance']) if row['balance'] else None
        row['source_row'] = int(row['source_row'])
        row['description'] = safe_text(row['description'])
    if not records:
        raise ValueError('No transactions')
    return records


def totals(records):
    incoming = sum((r['amount'] for r in records if r['amount'] > 0), ZERO)
    outgoing = -sum((r['amount'] for r in records if r['amount'] < 0), ZERO)
    return {'count': len(records), 'start': min(r['date'] for r in records),
            'end': max(r['date'] for r in records), 'money_in': incoming,
            'money_out': outgoing, 'net': incoming - outgoing}


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proof_path(path):
    return Path(str(path) + '.reconciled.json')


def reconcile(path, opening=None, closing=None, deposits=None, withdrawals=None, source=None,
              liability=False):
    records = read_transactions(path)
    sources = sorted(set(r['source_file'] for r in records))
    if source is None and len(sources) > 1:
        raise ValueError('Reconcile each statement separately with --source ' + ', '.join(sources))
    source = source or sources[0]
    rows = [r for r in records if r['source_file'] == source]
    if not rows:
        raise ValueError('Unknown source')
    result = totals(rows)
    issues, checks = [], []
    controls = {'opening': opening, 'closing': closing, 'deposits': deposits, 'withdrawals': withdrawals}
    # Once supplied, statement controls remain available after edits and rechecks.
    previous = load_json(proof_path(path)) if proof_path(path).exists() else {}
    saved = previous.get('failed_controls', {}).get(source, {})
    saved = saved or previous.get('sources', {}).get(source, {}).get('controls', {})
    for key in controls:
        if controls[key] is None:
            controls[key] = saved.get(key)
    liability = liability or previous.get('liability', {}).get(source, False)
    controls = {k: money(v, blank=False) if v is not None else None for k, v in controls.items()}
    opening, closing, deposits, withdrawals = [controls[k] for k in controls]
    # Card statement balances are amounts owed. --liability converts them to signed assets.
    if liability:
        opening = -opening if opening is not None else None
        closing = -closing if closing is not None else None
    for key, expected in [('money_in', deposits), ('money_out', withdrawals)]:
        if expected is not None:
            delta = result[key] - abs(expected)
            checks.append(key)
            if delta:
                issues.append(f'{key} differs by {dollars(delta)} (list minus statement)')
    if opening is not None and closing is not None:
        delta = opening + result['net'] - closing
        checks.append('opening + inflows - outflows = closing')
        if delta:
            issues.append(f'closing balance differs by {dollars(delta)} (list minus statement)')
    balances = [r['balance'] is not None for r in rows]
    if any(balances) and not all(balances):
        issues.append('Running balances are missing on some rows')
    if all(balances):
        candidates = []
        for ordered in (rows, list(reversed(rows))):
            if any(a['date'] > b['date'] for a, b in zip(ordered, ordered[1:])):
                continue
            discrepancies = []
            b = lambda r: -r['balance'] if liability else r['balance']
            for before, after in zip(ordered, ordered[1:]):
                delta = b(before) + after['amount'] - b(after)
                if delta:
                    discrepancies.append(f'{after["id"]}: running balance differs by {dollars(delta)}')
            if opening is not None and opening + ordered[0]['amount'] != b(ordered[0]):
                discrepancies.append('first balance differs by ' + dollars(opening + ordered[0]['amount'] - b(ordered[0])))
            if closing is not None and b(ordered[-1]) != closing:
                discrepancies.append('last balance differs by ' + dollars(b(ordered[-1]) - closing))
            candidates.append(discrepancies)
        best = min(candidates, key=len) if candidates else ['Rows are not in statement order']
        issues.extend(best)
        if len(rows) >= 2 or opening is not None:
            checks.append('running balances')
    sufficient = ('running balances' in checks or opening is not None and closing is not None
                  or deposits is not None and withdrawals is not None)
    if not all(balances) and ((opening is None) != (closing is None)):
        issues.append('Supply both opening and closing balances to check the provided balance')
    stamp = {'sha256': fingerprint(path), 'sources': {}}
    if proof_path(path).exists():
        previous = load_json(proof_path(path))
        if previous.get('sha256') == stamp['sha256']:
            stamp = previous
    stamp['sources'].pop(source, None)
    stamp.setdefault('liability', {})[source] = liability
    if issues:
        stamp.setdefault('failed_controls', {})[source] = clean_json(controls)
        save_json(proof_path(path), stamp)
        raise ValueError('Reconciliation failed:\n' + '\n'.join(issues))
    stamp.get('failed_controls', {}).pop(source, None)
    result.update(source=source, status='reconciled' if sufficient else 'unverified', checks=checks, controls=controls,
                  note=(UNVERIFIED_NOTICE if not sufficient else
                        'Running balances checked; statement totals would also check the endpoints.'
                        if opening is None or closing is None else 'Statement totals and balances match.'))
    stamp['sources'][source] = clean_json(result)
    save_json(proof_path(path), stamp)
    return result


def require_reconciled(path, records):
    if not proof_path(path).exists():
        raise ValueError('Run reconcile successfully before continuing')
    stamp = load_json(proof_path(path))
    if stamp.get('sha256') != fingerprint(path):
        raise ValueError('Transactions changed; run reconcile again')
    missing = set(r['source_file'] for r in records) - set(stamp.get('sources', {}))
    if missing:
        raise ValueError('Unreconciled sources: ' + ', '.join(sorted(missing)))
    return stamp


def verification_status(proof):
    return 'reconciled' if all(s.get('status') == 'reconciled' for s in proof['sources'].values()) else 'unverified'


def merchant(description):
    value = safe_text(description).upper().strip().lstrip("'")
    value = re.sub(r'^(?:(?:POS DEBIT|POS PURCHASE|DEBIT CARD PURCHASE|DEBIT CARD|CHECKCARD|PURCHASE|POS)\s+)+', '', value)
    value = re.sub(r'^(?:SQ\s*\*|TST\s*\*)\s*', '', value)
    value = re.sub(r'\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b', '', value)
    value = re.sub(r'\b(?:CARD|ACCT|ACCOUNT)(?: ENDING)?\s*\*?\*?\*?\*?\d{4}\b|\*{4}\d{4}', '', value)
    value = re.sub(r'\b(?:STORE|LOCATION|TERMINAL)\s*#?\s*\d+\b|#\s*\d+\b', '', value)
    # Known cities only: blindly deleting trailing words would merge unrelated merchants.
    cities = 'TAMPA|ST PETERSBURG|ORLANDO|RALEIGH|DURHAM|CHARLOTTE|AUSTIN|COLUMBUS|DENVER|NEW YORK|SAN FRANCISCO|SEATTLE|LOS ANGELES|CHICAGO'
    value = re.sub(r'\s+(?:' + cities + r')\s+[A-Z]{2}(?:\s+US)?\s*$', '', value)
    value = re.sub(r'\s+\d{3,4}(?:\s+[A-Z]{2})?\s*$', '', value)
    value = re.sub(r'\s+', ' ', value).strip(' *-')
    # Preserve service distinctions: Amazon retail/Prime; Uber rides/Eats/One.
    if re.match(r'(?:DOORDASH|DD ?\*)', value) and 'DASHPASS' not in value:
        return 'DOORDASH'
    if re.match(r'UBER\s*\*?\s*EATS', value):
        return 'UBER EATS'
    if re.match(r'AMZN MKTP|AMAZON MKTPLACE|AMAZON.COM\*', value):
        return 'AMAZON SHOPPING'
    return value or 'UNKNOWN MERCHANT'


def merchants(path, output):
    records = read_transactions(path)
    require_reconciled(path, records)
    groups = {}
    for row in records:
        key = merchant(row['description'])
        group = groups.setdefault(key, {'count': 0, 'total': ZERO, 'money_out': ZERO, 'lines': [], 'descriptions': []})
        group['count'] += 1
        group['total'] += row['amount']
        group['money_out'] += max(ZERO, -row['amount'])
        group['lines'].append(row['id'])
        if row['description'] not in group['descriptions']:
            group['descriptions'].append(row['description'])
    save_json(output, groups)
    return groups


def categorized(records, categories):
    keys = set(merchant(r['description']) for r in records)
    errors = []
    for key in sorted(keys):
        entry = categories.get(key)
        if not isinstance(entry, dict) or entry.get('category') not in CATEGORIES or not entry.get('name', '').strip():
            lines = ', '.join(r['id'] for r in records if merchant(r['description']) == key)
            errors.append(f'{key}: missing/invalid category or plain name ({lines})')
        elif entry['category'] == 'Subscriptions':
            if entry.get('kind') not in SUBSCRIPTION_KINDS:
                errors.append(f'{key}: subscription kind required: ' + ', '.join(SUBSCRIPTION_KINDS))
            if entry.get('billing') not in BILLING:
                errors.append(f'{key}: billing must be monthly, yearly or unclear')
    if set(categories) - keys:
        errors.append('Unknown merchant keys: ' + ', '.join(sorted(set(categories) - keys)))
    if errors:
        raise ValueError('Categorization incomplete:\n' + '\n'.join(errors))
    result = []
    for row in records:
        key = merchant(row['description'])
        entry = categories[key]
        result.append(dict(row, merchant=key, category=entry['category'], name=safe_text(entry['name']), flags=[]))
    return result


def group_stats(rows, days):
    total = -sum((r['amount'] for r in rows), ZERO)
    return {'count': len(rows), 'total': total, 'per_week': rounded(total * 7 / Decimal(days)),
            'count_per_week': rounded(Decimal(len(rows)) * 7 / Decimal(days)),
            'lines': [r['id'] for r in rows]}


def category_totals(records):
    sums = {c: ZERO for c in CATEGORIES}
    for row in records:
        sums[row['category']] += row['amount'] if row['category'] == 'Income' else -row['amount']
    return sums


def half(value):
    # An odd cent cannot be divided into spendable cents. Never exceed a half cut.
    return (value / 2).quantize(CENT, rounding='ROUND_DOWN')


def subscription_summary(recurring, categories):
    items = []
    for group in recurring:
        meta = categories[group['merchant']]
        billing, kind = meta.get('billing'), meta.get('kind')
        if billing not in BILLING or kind not in SUBSCRIPTION_KINDS:
            raise ValueError(group['merchant'] + ': recurring charge needs billing (monthly/yearly/unclear) '
                             'and kind (' + ', '.join(SUBSCRIPTION_KINDS) + ')')
        amount = money(group['total'])
        # One unusually large charge needs an explicit explanation before annualizing it.
        if billing == 'monthly' and amount / group['count'] > 60 and not meta.get('billing_reason', '').strip():
            raise ValueError(group['merchant'] + ': charge over $60; use billing unclear or give billing_reason confirming monthly billing')
        monthly = None if billing == 'unclear' else rounded(amount / 12) if billing == 'yearly' else amount
        items.append({'merchant': group['merchant'], 'name': group['name'], 'amount': amount,
                      'billing': billing, 'kind': kind, 'monthly': monthly,
                      'yearly': None if monthly is None else amount if billing == 'yearly' else monthly * 12,
                      'where': safe_text(meta.get('where', 'Check the original billing provider’s subscriptions page.')),
                      'lines': group['lines']})
    monthly_items = [i for i in items if i['billing'] == 'monthly']
    yearly_items = [i for i in items if i['billing'] == 'yearly']
    monthly_billed = sum((i['monthly'] for i in monthly_items), ZERO)
    yearly_equivalent = sum((i['monthly'] for i in yearly_items), ZERO)
    monthly = monthly_billed + yearly_equivalent
    return {'items': items, 'count': len(monthly_items), 'listed_count': len(items),
            'yearly_count': len(yearly_items), 'monthly_billed': monthly_billed,
            'yearly_equivalent': yearly_equivalent, 'monthly': monthly,
            'yearly': monthly_billed * 12 + sum((i['amount'] for i in yearly_items), ZERO),
            'unclear': [i for i in items if i['billing'] == 'unclear']}


def subscription_overlaps(subscriptions):
    groups = {}
    bundles, hulu = [], []
    for item in subscriptions['items']:
        kinds = {item['kind']}
        identity = (item['merchant'] + ' ' + item['name']).upper()
        if re.search(r'AMAZON PRIME|AMZN.*PRIME', identity):
            kinds.add('video')  # Prime Video is included, even when kind is shopping membership.
        if 'YOUTUBE' in identity and 'PREMIUM' in identity:
            kinds.add('music')  # YouTube Music is included in Premium.
        if 'DISNEY' in identity and 'BUNDLE' in identity:
            bundles.append(item)
        elif 'HULU' in identity:
            hulu.append(item)
        for kind in sorted(kinds):
            groups.setdefault(kind, []).append(item)
    result = []
    if bundles and hulu:
        groups['bundle:hulu'] = bundles + hulu
    for kind, items in sorted(groups.items()):
        if len(items) < 2:
            continue
        result.append({'id': kind, 'name': 'Hulu in the Disney bundle' if kind == 'bundle:hulu' else kind,
                       'merchants': [i['merchant'] for i in items], 'names': [i['name'] for i in items],
                       'lines': [line for i in items for line in i['lines']],
                       'note': 'Check included Hulu plan against standalone Hulu.' if kind == 'bundle:hulu' else
                               'Services may complement each other; review before canceling.'})
    return result


def fee_candidates(records):
    groups = {}
    for row in records:
        amount = money(row['amount'])
        if amount >= 0 or (row['category'] != 'Bank Fees & Interest' and not FEE.search(row['description'])):
            continue
        desc = row['description'].upper()
        if re.search(r'INTEREST|FINANCE CHARGE', desc):
            key, name = 'interest', 'Interest charges'
        elif re.search(r'OVERDRAFT|NSF|INSUFFICIENT|RETURNED', desc):
            key, name = 'overdraft-nsf', 'Overdraft and NSF fees'
        elif 'ATM' in desc:
            key, name = 'atm', 'ATM fees'
        elif re.search(r'MAINTENANCE|MONTHLY.*SERVICE', desc):
            key, name = 'maintenance', 'Monthly maintenance fee'
        elif 'FOREIGN' in desc:
            key, name = 'foreign', 'Foreign transaction fees'
        elif 'LATE' in desc:
            key, name = 'late', 'Late fees'
        else:
            key, name = 'other', 'Other bank fees'
        item = groups.setdefault(key, {'id': key, 'what': name, 'lines': [], 'monthly': ZERO,
                                      'kind': 'check' if key == 'interest' else 'observed'})
        item['lines'].append(row['id'])
        item['monthly'] -= amount
    return list(groups.values())


def analyze(path, categories_path, output, month=None):
    raw = read_transactions(path)
    proof = require_reconciled(path, raw)
    categories = load_json(categories_path)
    records = categorized(raw, categories)
    months = sorted(set(r['date'][:7] for r in records))
    if month is None and len(months) != 1:
        raise ValueError('Choose one complete budget month with --month YYYY-MM; available: ' + ', '.join(months))
    month = month or months[0]
    if month not in months:
        raise ValueError('No transactions in requested month')
    selected = [r for r in records if r['date'].startswith(month)]
    y, m = map(int, month.split('-'))
    days = calendar.monthrange(y, m)[1]
    recurring, doubles, fees = [], [], []
    outflows = [r for r in selected if r['amount'] < 0 and r['category'] not in ('Transfers', 'Savings', 'Income')]
    for key in sorted(set(r['merchant'] for r in outflows)):
        here = [r for r in outflows if r['merchant'] == key]
        history = sorted([r for r in records if r['merchant'] == key and r['amount'] < 0], key=lambda r: r['date'])
        amounts = [-r['amount'] for r in history]
        gaps = [(date.fromisoformat(b['date']) - date.fromisoformat(a['date'])).days for a, b in zip(history, history[1:])]
        regular = (len(gaps) >= 2 and min(gaps) >= 6 and max(gaps) <= 40 and max(gaps) - min(gaps) <= 3
                   and max(amounts) - min(amounts) <= max(amounts) * Decimal('.05'))
        monthly_pair = len(gaps) == 1 and 25 <= gaps[0] <= 35 and max(amounts) - min(amounts) <= max(amounts) * Decimal('.05')
        known = here[0]['category'] == 'Subscriptions' or bool(SUBSCRIPTION.search(key)) or 'billing' in categories[key]
        is_fee = here[0]['category'] == 'Bank Fees & Interest' or bool(FEE.search(here[0]['description']))
        if not is_fee and (known or regular or monthly_pair):
            recurring.append({'merchant': key, 'name': here[0]['name'], **group_stats(here, days),
                              'basis': 'subscription candidate; confirm plan and billing interval' if known else 'similar amount at regular gaps',
                              'gaps_days': gaps})
            for r in here:
                r['flags'].append('subscription' if known else 'recurring')
        ordered = sorted(here, key=lambda r: r['date'])
        for i, first in enumerate(ordered):
            for second in ordered[i+1:]:
                gap = (date.fromisoformat(second['date']) - date.fromisoformat(first['date'])).days
                if gap > 3:
                    break
                if first['amount'] == second['amount']:
                    doubles.append({'merchant': key, 'amount': -first['amount'],
                                    'lines': [first['id'], second['id']], 'label': 'check this',
                                    'note': 'Could be two legitimate purchases. No refund assumed.'})
                    for r in (first, second):
                        if 'possible double charge' not in r['flags']:
                            r['flags'].append('possible double charge')
    for row in outflows:
        if row['category'] == 'Bank Fees & Interest' or FEE.search(row['description']):
            row['flags'].append('fee')
            fees.append(row)
        if row['category'] == 'Delivery & Takeout':
            row['flags'].append('delivery')
    delivery = [r for r in outflows if r['category'] == 'Delivery & Takeout']
    visible = [r for r in delivery if re.search(r'\b(?:TIP|DELIVERY FEE|SERVICE FEE)\b', r['description'], re.I)]
    # Only separately posted fee/tip lines are summed. Never guess a receipt split.
    habits = []
    if delivery:
        stats = group_stats(delivery, days)
        habits.append({'habit': 'delivery', 'what': f'Delivery, {stats["count"]} orders',
                       'category': 'Delivery & Takeout', **stats,
                       'monthly': half(stats['total']), 'action': 'Order half as often; keep easy meals at home.'})
    for key in sorted(set(r['merchant'] for r in outflows)):
        rows = [r for r in outflows if r['merchant'] == key and r['category'] in FLEXIBLE
                and r['category'] != 'Delivery & Takeout' and -r['amount'] <= 15]
        if len(rows) >= 4:
            stats = group_stats(rows, days)
            name = rows[0]['name']
            habits.append({'habit': 'merchant:' + key, 'merchant': key, 'what': name + ', ' + str(len(rows)) + ' visits',
                           'category': rows[0]['category'], **stats, 'monthly': half(stats['total']),
                           'action': 'Make half as many of these small purchases.'})
    sums = category_totals(selected)
    income = sums['Income']
    spent = sum((v for c, v in sums.items() if c not in ('Income', 'Transfers', 'Savings')), ZERO)
    subscriptions = subscription_summary(recurring, categories)
    result = {'schema': 2, 'month': month, 'reconciliation': proof, 'statement_totals': totals(selected),
              'income': income, 'spending': spent, 'difference': income - spent, 'categories': sums,
              'verification': verification_status(proof),
              'subscriptions': subscriptions, 'overlaps': subscription_overlaps(subscriptions),
              'fee_leaks': fee_candidates(selected),
              'recurring': recurring, 'possible_doubles': doubles, 'fees': group_stats(fees, days),
              'delivery': {**group_stats(delivery, days), 'visible_fees_tips': group_stats(visible, days),
                           'note': 'Fees/tips inside a combined charge are not visible.'},
              'habit_leaks': habits, 'small_habits': [h for h in habits if h['habit'] != 'delivery'], 'transactions': selected,
              'notes': ['Transfers and card payments excluded; purchase refunds reduce their spending category.',
                        'Income means deposits Claude marked as regular income, not every positive entry.',
                        'A single month suggests subscriptions; it does not prove a trial, unused service, or billing interval.']}
    save_json(output, result)
    return result


def validate_plan(analysis, plan):
    if analysis.get('schema') != 2 or not analysis.get('reconciliation', {}).get('sources'):
        raise ValueError('Rerun analyze for current billing, overlap and fee checks, with its verification status')
    records = []
    for raw in analysis['transactions']:
        row = dict(raw, amount=money(raw['amount'], blank=False))
        row['description'] = safe_text(row['description'])
        row['date'] = parse_date(row['date'])
        if row['category'] not in CATEGORIES:
            raise ValueError('Unknown analysis category')
        records.append(row)
    ids = {r['id']: r for r in records}
    if len(ids) != len(records):
        raise ValueError('Duplicate analysis line IDs')
    actual = category_totals(records)
    if any(money(analysis['categories'][c]) != actual[c] for c in CATEGORIES):
        raise ValueError('Analysis totals changed; rerun analyze')
    income = actual['Income']
    spending = sum((v for c, v in actual.items() if c not in ('Income', 'Transfers', 'Savings')), ZERO)
    if money(analysis['income']) != income or money(analysis['spending']) != spending:
        raise ValueError('Analysis headline totals changed; rerun analyze')
    supplied_income = plan.get('take_home_pay')
    if supplied_income is not None:
        if income > 0:
            raise ValueError('Take-home pay is only for adding income missing from the statement')
        income = money(supplied_income, blank=False)
        if income <= 0:
            raise ValueError('Take-home pay must be positive and supplied by the person')
    card_only = income <= 0
    if card_only and any(k in plan for k in ('buffer', 'buffer_goal', 'buffer_current')):
        raise ValueError('A no-income spending plan has no Savings or buffer')
    required_categories = set(CATEGORIES) - ({'Income', 'Savings'} if card_only else set())
    target = plan.get('targets', {})
    errors = []
    if set(target) != required_categories:
        raise ValueError('Exactly one target per category required. Missing: '
                         + ', '.join(sorted(required_categories-set(target))) + '; unknown: '
                         + ', '.join(sorted(set(target)-required_categories)))
    amounts, reasons = {c: ZERO for c in CATEGORIES}, {c: '' for c in CATEGORIES}
    for c in CATEGORIES:
        if c not in required_categories:
            continue
        if not isinstance(target[c], dict) or 'amount' not in target[c]:
            raise ValueError(c + ': needs amount and why')
        amounts[c] = money(target[c]['amount'], blank=False)
        reasons[c] = safe_text(target[c].get('why', '').strip())
        if amounts[c] < 0:
            errors.append(c + ': target cannot be negative')
        baseline = max(ZERO, actual[c])
        if c in FIXED and amounts[c] != baseline:
            errors.append(c + ': fixed bill must stay at its observed cost')
        if c in FLEXIBLE and baseline > 0:
            if amounts[c] == 0:
                errors.append(c + ': a used flexible line cannot be zero')
            if amounts[c] < (baseline / 2).quantize(CENT, rounding='ROUND_CEILING'):
                errors.append(c + ': cannot cut more than half')
        if amounts[c] < baseline and c not in ('Income', 'Transfers') and not reasons[c]:
            errors.append(c + ': every cut needs a reason')
    if not card_only and amounts['Income'] != income:
        errors.append('Income must equal the regular income actually received')
    if amounts['Transfers'] != ZERO:
        errors.append('Transfers target must be zero; do not budget card payments twice')
    if not card_only and amounts['Entertainment'] <= ZERO:
        errors.append('Entertainment needs a positive guilt-free fun amount')
    allocated = sum((v for c, v in amounts.items() if c not in ('Income', 'Transfers')), ZERO)
    if card_only and allocated > spending:
        errors.append('Spending targets exceed last month by ' + dollars(allocated-spending))
    if not card_only and allocated != income:
        errors.append('Budget does not add up to income: differs by ' + dollars(allocated-income))
    buffer = ZERO if card_only else money(plan.get('buffer', ''), blank=False)
    goal = ZERO if card_only else money(plan.get('buffer_goal', ''), blank=False)
    current = ZERO if card_only else money(plan.get('buffer_current', ''), blank=False)
    if not card_only and (min(buffer, goal) < 0 or goal <= 0):
        errors.append('Set a positive buffer_goal and nonnegative buffer; buffer_current may be negative for an overdraft')
    required = min(amounts['Savings'], max(ZERO, goal-current))
    if buffer != required:
        errors.append('Savings must fill the buffer first: buffer should be ' + dollars(required))
    claims, leaks, leak_by_category = {}, [], {c: ZERO for c in CATEGORIES}
    habit_lines = set()
    for habit in analysis.get('habit_leaks', []):
        lines = habit['lines']
        monthly = half(-sum((ids[i]['amount'] for i in lines), ZERO))
        if monthly != money(habit['monthly']):
            raise ValueError('Habit totals changed; rerun analyze')
        habit_lines.update(lines)
        for i in lines:
            claims[i] = Decimal('0.5')
        leak_by_category[habit['category']] += monthly
        leaks.append({'what': habit['what'], 'monthly': monthly, 'yearly': monthly * 12,
                      'action': habit['action'], 'where': '', 'lines': lines, 'kind': 'habit'})
    # Recompute from source lines so deleting an analysis candidate cannot hide a fee.
    fee_groups = fee_candidates(records)
    fee_lines = {i for group in fee_groups for i in group['lines']}
    fee_actions = plan.get('fee_actions', {})
    if not isinstance(fee_actions, dict) or set(fee_actions) != {g['id'] for g in fee_groups}:
        raise ValueError('Every fee and interest group needs fee_actions: ' + ', '.join(g['id'] for g in fee_groups))
    for group in fee_groups:
        decision = fee_actions[group['id']]
        if not isinstance(decision, dict) or not isinstance(decision.get('action'), str) or not decision['action'].strip():
            raise ValueError(group['id'] + ': every fee and interest charge needs an action')
        kind = decision.get('kind', group['kind'])
        if kind not in ('observed', 'check') or (group['id'] == 'interest' and kind != 'check'):
            raise ValueError('Fees use observed or check; interest must remain check, with no promised savings')
        action = safe_text(decision['action'])
        if group['id'] == 'interest':
            action = 'Pay the balance down or in full when you can. ' + action + ' Future interest depends on the balance, rate and timing. Next month’s interest may not be zero.'
        if kind != 'check':
            for i in group['lines']:
                claims[i] = Decimal('1')
                leak_by_category[ids[i]['category']] -= ids[i]['amount']
        leaks.append({'what': group['what'], 'monthly': group['monthly'],
                      'yearly': None if kind == 'check' else group['monthly'] * 12,
                      'action': action, 'where': '', 'lines': group['lines'], 'kind': kind})
    overlap_groups = subscription_overlaps(analysis['subscriptions'])
    overlap_ids = {g['id'] for g in overlap_groups}
    addressed = set()
    nonmonthly_lines = {i for item in analysis['subscriptions']['items']
                        if item['billing'] != 'monthly' for i in item['lines']}
    for raw in plan.get('leaks', []):
        lines = raw.get('lines', [])
        if not lines or len(set(lines)) != len(lines) or any(i not in ids for i in lines):
            raise ValueError('Each leak needs unique existing source line IDs')
        if any(ids[i]['amount'] >= 0 or ids[i]['category'] in ('Income', 'Transfers', 'Savings') for i in lines):
            raise ValueError('Leak lines must be spending outflows')
        if fee_lines.intersection(lines):
            raise ValueError('Fee and interest rows are automatic; use fee_actions, not plan.leaks')
        share_raw = raw.get('share', '1')
        if isinstance(share_raw, (float, bool)):
            raise ValueError('Leak share must be a decimal string')
        share = Decimal(share_raw)
        if not share.is_finite() or not ZERO < share <= 1:
            raise ValueError('Leak share must be greater than 0 and at most 1')
        kind = raw.get('kind')
        if kind not in ('recurring', 'observed', 'check'):
            raise ValueError('Leak kind must be recurring, observed or check')
        for key in ('what', 'action'):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValueError('Leak needs plain what and action')
        if kind != 'check' and habit_lines.intersection(lines):
            raise ValueError('Habit cuts are fixed at half by the script; omit habit lines from plan leaks')
        overlap = raw.get('overlap')
        if overlap is not None:
            if overlap not in overlap_ids or overlap in addressed:
                raise ValueError('Unknown or repeated overlap review: ' + str(overlap))
            group = next(g for g in overlap_groups if g['id'] == overlap)
            if kind == 'check':
                if (set(lines) != set(group['lines']) or not isinstance(raw.get('reason'), str)
                        or not raw['reason'].strip() or '\n' in raw['reason']):
                    raise ValueError(overlap + ': overlap check needs every group line and a one-line reason')
            else:
                keep = raw.get('keep')
                cancelled = {ids[i]['merchant'] for i in lines}
                if keep not in group['merchants'] or cancelled != set(group['merchants']) - {keep} or share != 1:
                    raise ValueError(overlap + ': keep one service and reference all other services, or use a check row')
                expected = {i for i in group['lines'] if ids[i]['merchant'] != keep}
                if set(lines) != expected:
                    raise ValueError(overlap + ': include every charge for the services to cancel')
            addressed.add(overlap)
        if kind != 'check' and nonmonthly_lines.intersection(lines):
            raise ValueError('Billing unclear or yearly: use a check row; do not assume this charge repeats next month')
        monthly = rounded(-sum((ids[i]['amount'] for i in lines), ZERO) * share)
        if kind == 'check':
            pairs = [p for p in analysis['possible_doubles'] if set(lines) <= set(p['lines'])]
            if pairs:
                # Both evidence lines stay visible; only ONE extra charge is questioned.
                monthly = money(pairs[0]['amount'])
                lines = pairs[0]['lines']
        if kind != 'check':
            for i in lines:
                claims[i] = claims.get(i, ZERO) + share
                if claims[i] > 1:
                    errors.append(i + ': leaks double-count the same dollars')
            for c in CATEGORIES:
                leak_by_category[c] += rounded(-sum((ids[i]['amount'] for i in lines if ids[i]['category'] == c), ZERO) * share)
        leaks.append({'what': safe_text(raw['what']), 'monthly': monthly, 'yearly': None if kind == 'check' else monthly * 12,
                      'action': safe_text(raw['action'] + (' Reason: ' + raw['reason'] if overlap and kind == 'check' else '')), 'where': safe_text(raw.get('where', '')),
                      'lines': lines, 'kind': kind})
    for group in overlap_groups:
        if group['id'] not in addressed:
            errors.append('Overlap needs a leak or check row: ' + group['id'] + ' (' + ', '.join(group['names']) + ')')
    for c in CATEGORIES:
        cut = max(ZERO, actual[c] - amounts[c])
        if leak_by_category[c] > cut:
            errors.append(c + ': the target must reflect the suggested leak cuts')
        if c in ('Subscriptions', 'Bank Fees & Interest') and cut > leak_by_category[c]:
            errors.append(c + ': identify the lines and actions behind every removable charge cut')
    assumptions = plan.get('assumptions', [])
    if any(not isinstance(a, str) for a in assumptions):
        errors.append('Assumptions must be plain text')
    if errors:
        raise ValueError('Plan refused:\n' + '\n'.join(errors))
    leaks.sort(key=lambda r: (r['kind'] == 'check', -r['monthly']))
    leakage = sum((r['monthly'] for r in leaks if r['kind'] != 'check'), ZERO)
    future_spend = allocated - amounts['Savings']
    return {'records': records, 'actual': actual, 'targets': amounts, 'reasons': reasons,
            'card_only': card_only, 'supplied_income': supplied_income is not None,
            'income': income, 'spending': spending, 'difference': income-spending,
            'leaks': leaks, 'leakage': leakage, 'leakage_yearly': leakage*12,
            'freed': spending-future_spend, 'buffer': buffer, 'buffer_end': current+buffer,
            'savings': amounts['Savings']-buffer, 'allocated': allocated,
            'assumptions': [safe_text(a) for a in assumptions]}


def source_labels(lines, records):
    by_id = {r['id']: r for r in records}
    labels = []
    for line in lines:
        r = by_id[line]
        when = date.fromisoformat(r['date'])
        labels.append(f"{when.month}/{when.day} {r['name']}")
    return ', '.join(labels)


def natural_list(values):
    if len(values) < 2:
        return ''.join(values)
    return ', '.join(values[:-1]) + (', and ' if len(values) > 2 else ' and ') + values[-1]


def build(analysis_path, plan_path, output, report):
    from make_xlsx import write_xlsx, formula
    if Path(output).resolve() == Path(report).resolve():
        raise ValueError('Workbook and report need different paths')
    inputs = {Path(analysis_path).resolve(), Path(plan_path).resolve()}
    if Path(output).resolve() in inputs or Path(report).resolve() in inputs:
        raise ValueError('Outputs must not overwrite inputs')
    analysis, plan = load_json(analysis_path), load_json(plan_path)
    v = validate_plan(analysis, plan)
    subscriptions = analysis['subscriptions']
    if v['card_only']:
        first = f'You spent {dollars(v["spending"])} on this card.'
    elif v['supplied_income']:
        first = f'Your take-home pay is {dollars(v["income"])}. You spent {dollars(v["spending"])}.'
    else:
        first = f'You brought in {dollars(v["income"])}. You spent {dollars(v["spending"])}.'
    if not v['card_only'] and v['difference'] < 0:
        first += f" That's {dollars(-v['difference'])} more than you made."
    second = (f'You pay for {subscriptions["count"]} monthly subscriptions: '
              f'{dollars(money(subscriptions["monthly_billed"]))} a month '
              f'({dollars(money(subscriptions["monthly_billed"]) * 12)} a year).')
    if subscriptions['yearly_count']:
        annual_label = 'subscription' if subscriptions['yearly_count'] == 1 else 'subscriptions'
        second += (f' Plus {subscriptions["yearly_count"]} yearly {annual_label}: '
                   f'{dollars(money(subscriptions["yearly_equivalent"]))} a month, yearly charges divided by 12.')
    unclear_notes = [f'plus {dollars(money(i["amount"]))} {i["name"]}, billing unclear: check it'
                     for i in subscriptions['unclear']]
    third = f'{dollars(v["leakage"])} a month is leaking ({dollars(v["leakage_yearly"])} a year).'
    top = natural_list([re.sub(r', (\d+ (?:orders|visits))$', r' (\1)', leak['what'])
                        for leak in v['leaks'] if leak['kind'] != 'check'][:3])
    if top:
        third += ' Top leaks: ' + top + '.'
    fourth = (f'This plan spends {dollars(v["freed"])} less a month.' if v['card_only'] else
              f'This budget frees {dollars(v["freed"])} a month.')
    headlines = [first, second, third, fourth]
    status = verification_status(analysis['reconciliation'])
    warning = UNVERIFIED_NOTICE if status == 'unverified' else ''
    disclaimer = 'This is a second look at your own numbers, not financial advice.'
    fine_print = [
        'Transfers are excluded. Refunds reduce spending. Card payments are not income.',
        'Confirm billing intervals and cancels. Yearly amounts are estimates; checks are excluded.',
        disclaimer]
    summary = []
    notices = []
    if warning:
        summary.append(['Unverified. ' + warning])
        notices.append(len(summary))
    if plan.get('notice'):
        summary.append([safe_text(plan['notice'])])
        notices.append(len(summary))
    headline_rows = []
    for headline in headlines:
        summary.append([headline])
        headline_rows.append(len(summary))
    summary += [['Money in', 'Not provided' if v['card_only'] else v['income']],
                ['Money out', v['spending']],
                ['Difference', 'Not available without income' if v['card_only'] else v['difference']],
                ['Subscriptions per month', money(subscriptions['monthly'])],
                ['Subscriptions per year', money(subscriptions['yearly'])],
                ['Leaks per month', v['leakage']], ['Leaks per year', v['leakage_yearly']],
                ['What the plan frees', v['freed']], ['Statement check', status.capitalize()]]
    for note in unclear_notes:
        summary.append([note])
        notices.append(len(summary))
    fine_rows = []
    for line in fine_print:
        summary.append([line])
        fine_rows.append(len(summary))
    billing_names = {'monthly': 'Monthly', 'yearly': 'Yearly, charge divided by 12',
                     'unclear': 'Billing unclear: check it'}
    sub_rows = [['Subscription', 'Paid this month', 'Billing', 'Monthly equivalent', 'Yearly estimate', 'Where to cancel']]
    for item in subscriptions['items']:
        sub_rows.append([item['name'], money(item['amount']), billing_names[item['billing']],
                         '' if item['monthly'] is None else money(item['monthly']),
                         '' if item['yearly'] is None else money(item['yearly']), item['where']])
    sub_end = len(sub_rows)
    sub_details = list(sub_rows)
    sub_total_label = f'Total: {subscriptions["count"]} monthly'
    if subscriptions['yearly_count']:
        sub_total_label += f', {subscriptions["yearly_count"]} yearly (spread over 12 months)'
    sub_rows.append([sub_total_label, '', '',
                     formula(f'SUM(D2:D{sub_end})', money(subscriptions['monthly'])) if sub_end > 1 else ZERO,
                     formula(f'SUM(E2:E{sub_end})', money(subscriptions['yearly'])) if sub_end > 1 else ZERO, ''])
    sub_total_row = len(sub_rows)
    sub_rows += [[note] for note in unclear_notes]
    budget = [['Category', 'Last month', "Next month's target", 'Change', 'Why']]
    excluded = {'Income', 'Transfers'} | ({'Savings'} if v['card_only'] else set())
    budget_cats = [c for c in CATEGORIES if c not in excluded]
    for c in budget_cats:
        n = len(budget)+1
        budget.append([c, v['actual'][c], v['targets'][c],
                       formula(f'C{n}-B{n}', v['targets'][c]-v['actual'][c]), v['reasons'][c]])
    end = len(budget)
    actual_sum = sum((v['actual'][c] for c in budget_cats), ZERO)
    total_label = 'Total spending' if v['card_only'] else 'Total assigned'
    total_note = 'Within last month’s spending.' if v['card_only'] else 'Every dollar has a job.'
    budget.append([total_label, formula(f'SUM(B2:B{end})', actual_sum),
                   formula(f'SUM(C2:C{end})', v['allocated']),
                   formula(f'SUM(D2:D{end})', v['allocated']-actual_sum), total_note])
    total_row = len(budget)
    if not v['card_only']:
        budget.extend([['Income', v['income'], v['income'], ZERO,
                        'Take-home pay supplied by you' if v['supplied_income'] else 'Regular income received'],
                       ['Buffer within Savings', '', v['buffer'], '', 'Already included in Savings'],
                       ['Buffer after allocation', '', v['buffer_end'], '', 'After restoring any negative starting balance']])
    budget += [['Transfers (excluded)', v['actual']['Transfers'], ZERO, '', 'Excluded from the totals above'],
               ['How to change this', '', '', '', 'Tell Claude what to keep, then rebuild.']]
    for assumption in v['assumptions']:
        budget.append(['Assumption', '', '', '', assumption])
    leak_rows = [['What', 'Monthly or one-off', 'Yearly', 'Action', 'Where to cancel', 'Charges']]
    for leak in v['leaks']:
        label = leak['what'] + (' (check this)' if leak['kind'] == 'check' else '')
        leak_rows.append([label, leak['monthly'], '' if leak['yearly'] is None else leak['yearly'],
                          leak['action'], leak['where'], source_labels(leak['lines'], v['records'])])
    charges = [['Date', 'Description', 'Amount', 'Category', 'Flag', 'Source line']]
    for r in sorted(v['records'], key=lambda r: (r['date'], r['source_file'], r['source_row'])):
        charges.append([date.fromisoformat(r['date']), r['description'], r['amount'],
                        r['category'], ', '.join(r['flags']), r['id']])
    sheets = [dict(name='Summary', rows=summary, widths=[38, 84], header_rows=[], freeze=False,
                   headline_rows=headline_rows, fine_rows=fine_rows, notice_rows=notices,
                   merge_rows=headline_rows+fine_rows+notices),
              dict(name='Subscriptions', rows=sub_rows, widths=[32, 21, 31, 17, 18, 70], totals=[sub_total_row],
                   merge_rows=list(range(sub_total_row+1, len(sub_rows)+1))),
              dict(name='Budget', rows=budget, widths=[25, 18, 22, 18, 70], totals=[total_row]),
              dict(name='Leaks', rows=leak_rows, widths=[36, 23, 17, 52, 48, 48]),
              dict(name='Every charge', rows=charges, widths=[18, 59, 17, 26, 34, 16], filter=True)]
    def md(value):
        if isinstance(value, Decimal):
            return dollars(value)
        return str(value).replace('|', '\\|').replace('\n', '<br>')
    def table(rows):
        return ['| ' + ' | '.join(md(x) for x in rows[0]) + ' |',
                '|' + '|'.join('---' for _ in rows[0]) + '|'] + [
                '| ' + ' | '.join(md(x) for x in row) + ' |' for row in rows[1:]]
    report_lines = []
    if warning:
        report_lines += ['Unverified. ' + warning, '']
    if plan.get('notice'):
        report_lines += [safe_text(plan['notice']), '']
    report_lines += ['# Your money, ' + analysis['month'], '']
    for line in headlines:
        report_lines += [line, '']
    metrics = [row for row in summary if len(row) == 2]
    report_lines += table([['Your numbers', 'Amount']] + metrics)
    report_lines += ['', '## Every subscription', ''] + table(sub_details)
    report_lines += ['', f'{sub_total_label}, {dollars(money(subscriptions["monthly"]))} a month '
                     f'({dollars(money(subscriptions["yearly"]))} a year).']
    report_lines += ['', *unclear_notes, '', '## Leaks', '']
    report_lines += table(leak_rows)
    report_lines += ['', '## Next month', '']
    report_budget = [budget[0]] + [[c, v['actual'][c], v['targets'][c], v['targets'][c]-v['actual'][c],
                                  v['reasons'][c]] for c in budget_cats]
    report_budget.append([total_label, actual_sum, v['allocated'], v['allocated']-actual_sum, total_note])
    report_lines += table(report_budget)
    if not v['card_only']:
        report_lines += ['', f'{dollars(v["buffer"])} goes toward the buffer; {dollars(v["savings"])} goes to longer-term savings.',
                         f'After restoring any negative starting balance, the buffer becomes {dollars(v["buffer_end"])}.']
    if v['assumptions']:
        report_lines += ['', '## Assumptions', ''] + ['- ' + md(a) for a in v['assumptions']]
    report_lines += ['', *fine_print]
    if v['card_only']:
        report_lines += ['', 'Share your monthly take-home pay if you want a full budget; I’ll rebuild this plan around it, including expenses on your other accounts.']
    report_lines.append('')
    write_xlsx(output, sheets)
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text('\n'.join(report_lines), encoding='utf-8')
    return {'headlines': headlines, 'verification': status, 'mode': 'card' if v['card_only'] else 'budget',
            'subscriptions': subscriptions, 'workbook': str(output), 'report': str(report),
            'leaks_monthly': v['leakage'], 'leaks_yearly': v['leakage_yearly'], 'freed': v['freed']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('normalize', help='Clean CSVs; negative always means outflow')
    p.add_argument('inputs', nargs='+')
    p.add_argument('-o', '--output', required=True)
    p.add_argument('--map', default='')
    p.add_argument('--card', action='store_true', help='Positive-purchase card layout; reverses unsigned amount convention, not debit/credit columns')
    p = sub.add_parser('reconcile', help='Check source controls to the cent and record proof')
    p.add_argument('input')
    for field in ('opening', 'closing', 'deposits', 'withdrawals', 'source'):
        p.add_argument('--' + field)
    p.add_argument('--liability', action='store_true', help='Card opening/closing/running balances are positive amounts owed')
    p = sub.add_parser('merchants', help='Group cleaned merchants, preserving every source line')
    p.add_argument('input')
    p.add_argument('-o', '--output', required=True)
    p = sub.add_parser('analyze', help='All sums and evidence-backed candidates')
    p.add_argument('input')
    p.add_argument('--categories', required=True)
    p.add_argument('--month', help='YYYY-MM, required for multi-month input')
    p.add_argument('-o', '--output', required=True)
    p = sub.add_parser('build', help='Validate plan; write Budget.xlsx and REPORT.md')
    p.add_argument('analysis')
    p.add_argument('plan')
    p.add_argument('-o', '--output', required=True)
    p.add_argument('--report', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'normalize':
            result = normalize(args.inputs, args.output, parse_map(args.map), args.card)
        elif args.command == 'reconcile':
            result = reconcile(args.input, args.opening, args.closing, args.deposits,
                               args.withdrawals, args.source, args.liability)
        elif args.command == 'merchants':
            groups = merchants(args.input, args.output)
            result = {'merchants': len(groups), 'output': args.output}
        elif args.command == 'analyze':
            analysis = analyze(args.input, args.categories, args.output, args.month)
            result = {k: analysis[k] for k in ('month', 'income', 'spending', 'difference')}
            result['output'] = args.output
        else:
            result = build(args.analysis, args.plan, args.output, args.report)
        print(json.dumps(clean_json(result), indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation, csv.Error) as exc:
        print('Cannot continue: ' + safe_text(str(exc)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
