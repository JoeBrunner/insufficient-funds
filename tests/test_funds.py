"""All financial fixtures are fictional. Standard-library behavioral checks."""
import copy
import csv
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/insufficient-funds/scripts'
sys.path.insert(0, str(SCRIPTS))
import funds
import make_xlsx

KEY = json.loads((ROOT / 'tests/fixtures/answer-key.json').read_text())
SAMPLE = ROOT / 'examples/statement-2026-09.csv'
RUN = ROOT / 'examples/sample-run'
NS = {'x': make_xlsx.NS}


class Workspace(unittest.TestCase):
    def setUp(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def normalize(self, text, card=False, mapping=None):
        raw, clean = self.dir / 'source.csv', self.dir / 'clean.csv'
        raw.write_text(text, encoding='utf-8')
        result = funds.normalize([raw], clean, mapping, card)
        return funds.read_transactions(clean), result

    def example(self):
        clean = self.dir / 'transactions.csv'
        funds.normalize([SAMPLE], clean)
        s = KEY['summary']
        funds.reconcile(clean, s['opening'], s['closing'], s['deposits'], s['withdrawals'])
        return clean

    def analysis(self):
        clean = self.example()
        result = self.dir / 'analysis.json'
        funds.analyze(clean, RUN / 'work/categories.json', result)
        return result


class NormalizeTests(Workspace):
    def test_example_true_totals(self):
        clean = self.example()
        rows = funds.read_transactions(clean)
        self.assertEqual(len(rows), 98)
        t = funds.totals(rows)
        self.assertEqual(t['money_in'], Decimal('3425.00'))
        self.assertEqual(t['money_out'], Decimal('3845.35'))
        self.assertEqual(rows[-1]['balance'], Decimal('-125.35'))
        self.assertEqual(rows[0]['source_row'], 10)
        self.assertEqual(sum(r['amount'] for r in rows), Decimal('-420.35'))

    def test_signed_and_dates(self):
        rows, _ = self.normalize('Date,Description,Amount\n09/01/2026,Pay,1000\n9/2/26,Shop,-20\n2026-09-03,Refund,4.32\n')
        self.assertEqual([r['date'] for r in rows], ['2026-09-01','2026-09-02','2026-09-03'])
        self.assertEqual([r['amount'] for r in rows], [Decimal('1000'), Decimal('-20'), Decimal('4.32')])

    def test_debit_credit(self):
        rows, _ = self.normalize('Date,Description,Debit,Credit\n9/1/26,Pay,,100\n9/2/26,Shop,10,\n')
        self.assertEqual([r['amount'] for r in rows], [Decimal('100'), Decimal('-10')])

    def test_withdrawals_deposits(self):
        rows, _ = self.normalize('Date,Description,Withdrawals,Deposits\n9/1/26,Pay,,150\n9/2/26,Shop,12.30,\n')
        self.assertEqual(funds.totals(rows)['net'], Decimal('137.70'))

    def test_type_column(self):
        rows, _ = self.normalize('Date,Description,Amount,Type\n9/1/26,Pay,500,Credit\n9/2/26,Shop,25,Debit\n')
        self.assertEqual([r['amount'] for r in rows], [Decimal('500'), Decimal('-25')])

    def test_debit_credit_direction(self):
        rows, _ = self.normalize('Date,Description,Amount,Debit/Credit\n9/1/26,Pay,100,CR\n9/2/26,Shop,4.25,DR\n')
        self.assertEqual(funds.totals(rows)['net'], Decimal('95.75'))

    def test_unknown_direction_stops(self):
        with self.assertRaisesRegex(ValueError, 'Unknown direction'):
            self.normalize('Date,Description,Amount,Type\n9/1/26,Shop,20,Unclear\n')

    def test_payment_type_keeps_bank_sign(self):
        rows, _ = self.normalize('Date,Description,Amount,Type\n9/1/26,Loan,-20,Payment\n')
        self.assertEqual(rows[0]['amount'], Decimal('-20'))

    def test_card_positive_purchases(self):
        rows, reports = self.normalize('Date,Description,Amount\n9/1/26,Shop,25.99\n9/2/26,Payment,-100\n', card=True)
        self.assertEqual([r['amount'] for r in rows], [Decimal('-25.99'), Decimal('100')])
        self.assertIn('inverted', reports[0]['signs'])

    def test_amex_layout_auto_inverts(self):
        rows, _ = self.normalize('Date,Description,Amount,Extended Details,Appears On Your Statement As\n9/1/26,Shop,25.99,Info,Shop\n')
        self.assertEqual(rows[0]['amount'], Decimal('-25.99'))

    def test_capital_one_columns(self):
        rows, _ = self.normalize('Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit\n2026-09-01,2026-09-02,4417,Shop,Retail,23.41,\n2026-09-04,2026-09-05,4417,Refund,Retail,,2.31\n')
        self.assertEqual(rows[0]['date'], '2026-09-02')
        self.assertEqual(funds.totals(rows)['net'], Decimal('-21.10'))
        self.assertNotIn('4417', (self.dir/'clean.csv').read_text())

    def test_chase_checking(self):
        rows, _ = self.normalize('Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\nCREDIT,09/01/2026,Payroll,100,ACH_CREDIT,100,\nDEBIT,09/02/2026,Shop,-15,DEBIT_CARD,85,\n')
        self.assertEqual(funds.totals(rows)['net'], Decimal('85'))

    def test_chase_card(self):
        rows, _ = self.normalize('Transaction Date,Post Date,Description,Category,Type,Amount\n09/01/2026,09/02/2026,Shop,Shopping,Sale,-12.34\n09/03/2026,09/04/2026,Refund,Shopping,Return,1.23\n')
        self.assertEqual(funds.totals(rows)['net'], Decimal('-11.11'))

    def test_currency_parentheses_trailing_minus_blanks(self):
        rows, _ = self.normalize('Date,Description,Amount\n9/1/26,Pay,"$1,234.56"\n9/2/26,A,($12.34)\n9/3/26,B,5.67-\n9/4/26,Zero,\n')
        self.assertEqual([r['amount'] for r in rows], [Decimal('1234.56'),Decimal('-12.34'),Decimal('-5.67'),Decimal('0')])

    def test_junk_and_summary_preserve_physical_lines(self):
        rows, _ = self.normalize('Account export\nAccount,****4417\n\nDate,Description,Amount\n9/1/26,A,-1\nTotal,,-1\nEnding balance,,-1\n')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_row'], 5)

    def test_multiline_description_source_row(self):
        rows, _ = self.normalize('Date,Description,Amount\n9/1/26,"A\nB",-1\n9/2/26,C,-2\n')
        self.assertEqual([r['source_row'] for r in rows], [2,4])

    def test_map(self):
        rows, _ = self.normalize('When,Who,Value\n9/1/26,A,-1.23\n', mapping={'date':'When','description':'Who','amount':'Value'})
        self.assertEqual(rows[0]['amount'], Decimal('-1.23'))

    def test_map_separate_columns(self):
        rows, _ = self.normalize('When,Who,Out,In\n9/1/26,A,1.23,\n', mapping=funds.parse_map('date=When,description=Who,debit=Out,credit=In'))
        self.assertEqual(rows[0]['amount'], Decimal('-1.23'))

    def test_ambiguous_headers_listed(self):
        with self.assertRaisesRegex(ValueError, 'Headers:'):
            self.normalize('Date,Description,Amount,Transaction Amount\n9/1/26,A,5,5\n')

    def test_bad_transaction_not_skipped(self):
        with self.assertRaisesRegex(ValueError, 'S1:3'):
            self.normalize('Date,Description,Amount\n9/1/26,A,-2\n9/31/26,B,-4\n')

    def test_money_rejects_bad_values(self):
        for value in ('NaN','Infinity','1.001','abc', 1.2, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                funds.money(value)

    def test_mask_identifiers_and_csv_formula_text(self):
        rows, _ = self.normalize('Date,Description,Amount\n9/1/26,POS CARD 4111 1111 1111 4417 ACCT 1234567890,-12\n9/2/26,=1+1,-2\n')
        self.assertNotIn('4111 1111', rows[0]['description'])
        self.assertNotIn('1234567890', rows[0]['description'])
        self.assertIn('****4417', rows[0]['description'])
        self.assertEqual(rows[1]['description'], "'=1+1")

    def test_no_overwriting_source(self):
        raw = self.dir/'raw.csv'
        raw.write_text('Date,Description,Amount\n9/1/26,A,-1\n')
        with self.assertRaisesRegex(ValueError, 'differ'):
            funds.normalize([raw], raw)

    def test_same_statement_twice_stops(self):
        raw=self.dir/'raw.csv'
        raw.write_text('Date,Description,Amount\n9/1/26,A,-1\n')
        with self.assertRaisesRegex(ValueError,'more than once'):
            funds.normalize([raw,raw],self.dir/'out.csv')

    def test_merchant_named_total_is_not_a_summary(self):
        rows,_=self.normalize('Description,Date,Amount\nTOTAL WINE,9/1/26,-20\n')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['amount'],Decimal('-20'))

    def test_short_grouped_account_number_masked(self):
        self.assertNotIn('1234-5678',funds.safe_text('TRANSFER 1234-5678'))


class ReconcileTests(Workspace):
    def test_example_matches_all_controls(self):
        clean = self.example()
        proof = funds.load_json(funds.proof_path(clean))
        self.assertEqual(len(proof['sources']['S1']['checks']), 4)
        self.assertEqual(proof['sources']['S1']['status'], 'reconciled')

    def test_deleted_line_reports_exact_difference(self):
        text = 'Date,Description,Amount\n9/1/26,Pay,100\n9/2/26,A,-10\n'
        self.normalize(text)
        with self.assertRaisesRegex(ValueError, r'\$5.25'):
            funds.reconcile(self.dir/'clean.csv', '0', '84.75', '100', '15.25')

    def test_doubled_line_reports_exact_difference(self):
        self.normalize('Date,Description,Amount\n9/1/26,Pay,100\n9/2/26,A,-10\n9/2/26,A,-10\n')
        with self.assertRaisesRegex(ValueError, r'\$-10.00'):
            funds.reconcile(self.dir/'clean.csv', '0', '90', '100', '10')

    def test_running_balance_ascending_and_descending_same_day(self):
        for order in ('9/1/26,Pay,100,100\n9/1/26,A,-10,90\n9/2/26,B,-5,85\n',
                      '9/2/26,B,-5,85\n9/1/26,A,-10,90\n9/1/26,Pay,100,100\n'):
            with self.subTest(order=order):
                self.normalize('Date,Description,Amount,Running Balance\n' + order)
                result = funds.reconcile(self.dir/'clean.csv')
                self.assertIn('running balances', result['checks'])

    def test_balance_gap_fails(self):
        self.normalize('Date,Description,Amount,Balance\n9/1/26,Pay,100,100\n9/2/26,A,-10,85\n')
        with self.assertRaisesRegex(ValueError, r'\$5.00'):
            funds.reconcile(self.dir/'clean.csv')

    def test_no_controls_continues_unverified(self):
        self.normalize('Date,Description,Amount\n9/1/26,A,-1\n')
        result=funds.reconcile(self.dir/'clean.csv')
        self.assertEqual(result['status'],'unverified')
        self.assertEqual(result['note'],funds.UNVERIFIED_NOTICE)
        groups=funds.merchants(self.dir/'clean.csv',self.dir/'merchants.json')
        self.assertEqual(groups['A']['count'],1)

    def test_failed_controls_cannot_be_discarded(self):
        self.normalize('Date,Description,Amount\n9/1/26,A,-1\n')
        with self.assertRaisesRegex(ValueError,'differs'):
            funds.reconcile(self.dir/'clean.csv','0','0')
        with self.assertRaisesRegex(ValueError,'differs'):
            funds.reconcile(self.dir/'clean.csv')

    def test_controls_survive_transaction_edits(self):
        self.normalize('Date,Description,Amount\n9/1/26,A,-1\n')
        funds.reconcile(self.dir/'clean.csv','0','-1')
        self.normalize('Date,Description,Amount\n9/1/26,A,-2\n')
        with self.assertRaisesRegex(ValueError,'differs'):
            funds.reconcile(self.dir/'clean.csv')

    def test_no_controls_later_summary_reconciles(self):
        self.normalize('Date,Description,Amount\n9/1/26,A,-1\n')
        self.assertEqual(funds.reconcile(self.dir/'clean.csv')['status'],'unverified')
        self.assertEqual(funds.reconcile(self.dir/'clean.csv','0','1',liability=True)['status'],'reconciled')
        self.assertEqual(funds.reconcile(self.dir/'clean.csv')['status'],'reconciled')

    def test_changed_file_invalidates_proof(self):
        clean = self.example()
        clean.write_text(clean.read_text().replace('STARBUCKS', 'COFFEE', 1))
        with self.assertRaisesRegex(ValueError, 'changed'):
            funds.require_reconciled(clean, funds.read_transactions(clean))

    def test_failed_recheck_revokes_proof(self):
        clean = self.example()
        with self.assertRaises(ValueError):
            funds.reconcile(clean, '295', '-125.34')
        with self.assertRaisesRegex(ValueError, 'Unreconciled'):
            funds.require_reconciled(clean, funds.read_transactions(clean))

    def test_card_liability_equation(self):
        self.normalize('Date,Description,Amount\n9/1/26,Purchase,-100\n9/2/26,Payment,50\n')
        result = funds.reconcile(self.dir/'clean.csv', '200', '250', '50', '100', liability=True)
        self.assertEqual(result['status'], 'reconciled')

    def test_multiple_sources_need_separate_checks(self):
        a, b, out = self.dir/'a.csv', self.dir/'b.csv', self.dir/'combined.csv'
        a.write_text('Date,Description,Amount\n9/1/26,A,100\n')
        b.write_text('Date,Description,Amount\n9/1/26,B,-50\n')
        funds.normalize([a,b], out)
        with self.assertRaisesRegex(ValueError, 'each statement'):
            funds.reconcile(out, '0', '50')
        funds.reconcile(out, '0', '100', source='S1')
        with self.assertRaisesRegex(ValueError, 'S2'):
            funds.require_reconciled(out, funds.read_transactions(out))
        funds.reconcile(out, '100', '50', source='S2')
        funds.require_reconciled(out, funds.read_transactions(out))


class MerchantTests(unittest.TestCase):
    def test_prefix_store_date_city(self):
        for value in ['POS DEBIT STARBUCKS #1042 RALEIGH NC 09/01',
                      'SQ * STARBUCKS STORE 9876 TAMPA FL', 'TST* STARBUCKS #21 AUSTIN TX',
                      'STARBUCKS 1042', 'CHECKCARD 09/01 STARBUCKS #1042 RALEIGH NC']:
            with self.subTest(value=value):
                self.assertEqual(funds.merchant(value), 'STARBUCKS')

    def test_service_distinctions(self):
        self.assertEqual(funds.merchant('DOORDASH*CHIPOTLE'), 'DOORDASH')
        self.assertEqual(funds.merchant('UBER *EATS'), 'UBER EATS')
        self.assertNotEqual(funds.merchant('UBER *EATS'), funds.merchant('UBER *TRIP'))
        self.assertNotEqual(funds.merchant('AMZN MKTP US*Q1'), funds.merchant('AMAZON PRIME'))
        self.assertNotEqual(funds.merchant('DOORDASH DASHPASS'), funds.merchant('DOORDASH*CAVA'))


class AnalyzeTests(Workspace):
    def test_card_payment_credit_is_not_income(self):
        self.normalize('Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit\n'
                       '2026-09-01,2026-09-02,4417,Shop,Shopping,10,\n'
                       '2026-09-03,2026-09-03,4417,Card payment,Payment,,50\n')
        clean=self.dir/'clean.csv'
        funds.reconcile(clean)
        funds.save_json(self.dir/'cats.json', {'SHOP':{'name':'Shop','category':'Shopping'},
                                              'CARD PAYMENT':{'name':'Card payment','category':'Transfers'}})
        a=funds.analyze(clean,self.dir/'cats.json',self.dir/'a.json')
        self.assertEqual(a['income'],Decimal('0.00'))
        self.assertEqual(a['spending'],Decimal('10.00'))
        plan={'targets':{c:{'amount':'0.00','why':'Unused'} for c in funds.CATEGORIES if c not in ('Income','Savings')}}
        plan['targets']['Shopping']={'amount':'5.00','why':'Buy fewer optional items'}
        funds.save_json(self.dir/'p.json',plan)
        result=funds.build(self.dir/'a.json',self.dir/'p.json',self.dir/'card.xlsx',self.dir/'card.md')
        self.assertEqual(result['headlines'][0],'You spent $10.00 on this card.')
        self.assertEqual(result['headlines'][3],'This plan spends $5.00 less a month.')

    def test_full_subscription_list_includes_gym(self):
        a=funds.load_json(self.analysis())
        subs=a['subscriptions']
        self.assertEqual(subs['count'],13)
        self.assertEqual(subs['monthly'],'170.85')
        self.assertEqual(subs['yearly'],'2050.20')
        self.assertEqual({i['merchant'] for i in subs['items']},{r['merchant'] for r in a['recurring']})
        gym=next(i for i in subs['items'] if i['merchant']=='PLANET FITNESS')
        self.assertEqual(gym['monthly'],'15.00')
        for item in subs['items']:
            self.assertTrue(item['where'])
            self.assertTrue(item['billing'])

    def test_habit_cuts_are_half_and_round_down(self):
        a=funds.load_json(self.analysis())
        self.assertEqual(len(a['habit_leaks']),2)
        cuts={h['habit']:h['monthly'] for h in a['habit_leaks']}
        self.assertEqual(cuts,{'delivery':'305.03','merchant:STARBUCKS':'54.55'})
        for h in a['habit_leaks']:
            self.assertEqual(Decimal(h['monthly']), (Decimal(h['total'])/2).quantize(Decimal('.01'),rounding='ROUND_DOWN'))

    def test_subscription_billing_uses_decimal(self):
        groups=[{'merchant':'A','name':'Annual','total':Decimal('120'),'count':1,'lines':['S1:2']},
                {'merchant':'U','name':'Unknown','total':Decimal('209'),'count':1,'lines':['S1:3']}]
        subs=funds.subscription_summary(groups,{'A':{'billing':'yearly','kind':'software'},
                                              'U':{'billing':'unclear','kind':'fitness'}})
        self.assertEqual(subs['items'][0]['monthly'],Decimal('10.00'))
        self.assertIsNone(subs['items'][1]['monthly'])
        self.assertIsNone(subs['items'][1]['yearly'])
        self.assertEqual(subs['count'],0)
        self.assertEqual(subs['yearly_count'],1)
        self.assertEqual(subs['yearly'],Decimal('120.00'))

    def test_example_categories_and_true_totals(self):
        analysis = funds.load_json(self.analysis())
        for c in funds.CATEGORIES:
            self.assertEqual(analysis['categories'][c], KEY['categories'].get(c, '0.00'), c)
        self.assertEqual(analysis['income'], '3280.00')
        self.assertEqual(analysis['spending'], '3760.35')
        self.assertEqual(analysis['difference'], '-480.35')

    def test_recurring_all_planted_subscriptions(self):
        analysis = funds.load_json(self.analysis())
        lines = {i for group in analysis['recurring'] for i in group['lines']}
        self.assertEqual(lines, set(KEY['planted_leaks']['recurring']['lines']))
        self.assertEqual(len(analysis['recurring']), 13)

    def test_exact_double_charge(self):
        analysis = funds.load_json(self.analysis())
        self.assertEqual(len(analysis['possible_doubles']), 1)
        duplicate = analysis['possible_doubles'][0]
        self.assertEqual(duplicate['lines'], KEY['planted_leaks']['double_charge']['lines'])
        self.assertEqual(duplicate['amount'], '28.74')
        self.assertEqual(duplicate['label'], 'check this')

    def test_fees_delivery_coffee_match_key(self):
        analysis = funds.load_json(self.analysis())
        for field, tag in [('fees','fee'), ('delivery','delivery')]:
            a, k = analysis[field], KEY['planted_leaks'][tag]
            self.assertEqual(a['count'], k['count'])
            self.assertEqual(a['total'], k['monthly'])
            self.assertEqual(set(a['lines']), set(k['lines']))
        coffee = next(h for h in analysis['small_habits'] if h['merchant'] == 'STARBUCKS')
        self.assertEqual(coffee['total'], '109.11')
        self.assertEqual(coffee['per_week'], '25.46')
        self.assertEqual(analysis['delivery']['visible_fees_tips']['total'], '0.00')

    def test_uncategorized_lists_lines(self):
        clean = self.example()
        cats = funds.load_json(RUN/'work/categories.json')
        del cats['HULU']
        funds.save_json(self.dir/'categories.json', cats)
        with self.assertRaisesRegex(ValueError, 'HULU.*S1:14'):
            funds.analyze(clean, self.dir/'categories.json', self.dir/'analysis.json')

    def test_invalid_category(self):
        rows = [{'id':'S1:2', 'description':'A'}]
        with self.assertRaisesRegex(ValueError, 'category'):
            funds.categorized(rows, {'A': {'name':'A','category':'Magic'}})

    def test_fee_signals_without_category(self):
        for desc in ('OVERDRAFT FEE','INSUFFICIENT FUNDS','NSF FEE','RETURNED ITEM FEE',
                     'ATM FEE','ATM OPERATOR FEE','MONTHLY MAINTENANCE FEE',
                     'FOREIGN TRANSACTION FEE','LATE FEE','PURCHASE INTEREST','INTEREST CHARGE'):
            self.assertIsNotNone(funds.FEE.search(desc), desc)
        self.assertIsNone(funds.FEE.search('COFFEE SHOP'))

    def test_refunds_transfers_and_card_payments_not_income(self):
        self.normalize('Date,Description,Amount\n9/1/26,Pay,100\n9/2/26,Shop,-20\n9/3/26,Shop,5\n9/4/26,Card payment,-40\n9/5/26,Transfer,40\n')
        clean = self.dir/'clean.csv'
        funds.reconcile(clean, '0', '85')
        cats = {k:{'name':k, 'category':c} for k,c in [('PAY','Income'),('SHOP','Shopping'),('CARD PAYMENT','Transfers'),('TRANSFER','Transfers')]}
        funds.save_json(self.dir/'cats.json', cats)
        a = funds.analyze(clean, self.dir/'cats.json', self.dir/'a.json')
        self.assertEqual(a['income'], Decimal('100'))
        self.assertEqual(a['spending'], Decimal('15'))

    def test_multi_month_regular_gap_and_month_selection(self):
        self.normalize('Date,Description,Amount\n7/1/26,Club,-10\n8/1/26,Club,-10\n9/1/26,Club,-10\n9/2/26,Pay,100\n')
        clean=self.dir/'clean.csv'
        funds.reconcile(clean, '0', '70')
        funds.save_json(self.dir/'cats.json', {'CLUB':{'name':'Club','category':'Other','billing':'monthly','kind':'fitness'},'PAY':{'name':'Pay','category':'Income'}})
        with self.assertRaisesRegex(ValueError, 'Choose one'):
            funds.analyze(clean,self.dir/'cats.json',self.dir/'a.json')
        a=funds.analyze(clean,self.dir/'cats.json',self.dir/'a.json','2026-09')
        self.assertEqual(a['spending'],Decimal('10'))
        self.assertEqual(a['recurring'][0]['gaps_days'],[31,31])


class BuildTests(Workspace):
    def setUp(self):
        super().setUp()
        self.a_path = self.analysis()
        self.a = funds.load_json(self.a_path)
        self.plan = funds.load_json(RUN/'work/plan.json')

    def validate(self):
        return funds.validate_plan(self.a, self.plan)

    def build(self):
        p=self.dir/'plan.json'
        funds.save_json(p,self.plan)
        return funds.build(self.a_path,p,self.dir/'Budget.xlsx',self.dir/'REPORT.md')

    def test_accept_good_plan_exact_numbers(self):
        v=self.validate()
        self.assertEqual(v['allocated'],Decimal('3280.00'))
        self.assertEqual(v['leakage'],Decimal('508.49'))
        self.assertEqual(v['leakage_yearly'],Decimal('6101.88'))
        self.assertEqual(v['freed'],Decimal('685.41'))
        self.assertEqual(v['buffer'],Decimal('205.06'))
        self.assertEqual(v['buffer_end'],Decimal('79.71'))

    def card_example(self):
        # Same fictional charges as a Capital One-style export; no paychecks/controls.
        raw=self.dir/'card.csv'
        records=[r for r in funds.read_transactions(self.example()) if 'PAYROLL' not in r['description']]
        with raw.open('w',newline='') as stream:
            writer=csv.writer(stream)
            writer.writerow(['Transaction Date','Posted Date','Card No.','Description','Category','Debit','Credit'])
            for r in records:
                amount=r['amount']
                writer.writerow([r['date'],r['date'],'4417',r['description'],'',max(-amount,0) or '',max(amount,0) or ''])
        clean=self.dir/'card-clean.csv'
        funds.normalize([raw],clean)
        funds.reconcile(clean)
        groups=funds.merchants(clean,self.dir/'card-merchants.json')
        cats=funds.load_json(RUN/'work/categories.json')
        funds.save_json(self.dir/'card-categories.json',{k:cats[k] for k in groups})
        path=self.dir/'card-analysis.json'
        funds.analyze(clean,self.dir/'card-categories.json',path)
        a=funds.load_json(path)
        plan=copy.deepcopy(self.plan)
        for key in ('Income','Savings'):
            del plan['targets'][key]
        for key in ('buffer','buffer_goal','buffer_current'):
            del plan[key]
        # Source IDs change with this export; map original evidence by transaction order.
        mapping={old['id']:new['id'] for old,new in zip(records,a['transactions'])}
        for leak in plan['leaks']:
            leak['lines']=[mapping[i] for i in leak['lines']]
        plan['assumptions']=['Card spending only. Card payments are transfers.']
        return a,plan,path

    def test_unverified_card_full_build(self):
        a,p,path=self.card_example()
        funds.save_json(self.dir/'card-plan.json',p)
        result=funds.build(path,self.dir/'card-plan.json',self.dir/'card.xlsx',self.dir/'card.md')
        self.assertEqual(result['verification'],'unverified')
        self.assertEqual(result['mode'],'card')
        self.assertEqual(len(result['headlines']),4)
        self.assertEqual(result['headlines'][0],'You spent $3,760.35 on this card.')
        self.assertEqual(result['headlines'][3],'This plan spends $685.41 less a month.')
        report=(self.dir/'card.md').read_text()
        self.assertTrue(report.startswith('Unverified. '+funds.UNVERIFIED_NOTICE))
        self.assertEqual(report.count(funds.UNVERIFIED_NOTICE),1)
        self.assertNotIn('| Savings |',report)
        self.assertIn('take-home pay',report.splitlines()[-1])
        with zipfile.ZipFile(self.dir/'card.xlsx') as z:
            summary=z.read('xl/worksheets/sheet1.xml').decode()
            self.assertIn('Unverified',summary)
            budget=z.read('xl/worksheets/sheet3.xml').decode()
            self.assertNotIn('Savings',budget)
            self.assertNotIn('Buffer',budget)

    def test_card_bad_plans_refused(self):
        a,base,_=self.card_example()
        for category,amount,why,match in [('Groceries','0.00','Cut','cannot be zero'),
                ('Groceries','100.00','Cut','more than half'),('Housing','500.00','Cut','fixed bill'),
                ('Shopping','210.00','','reason'),('Shopping','1000.00','More','exceed last month')]:
            p=copy.deepcopy(base)
            p['targets'][category]={'amount':amount,'why':why}
            with self.subTest(category=category,amount=amount),self.assertRaisesRegex(ValueError,match):
                funds.validate_plan(a,p)
        p=copy.deepcopy(base)
        p['buffer']='0.00'
        with self.assertRaisesRegex(ValueError,'no Savings or buffer'):
            funds.validate_plan(a,p)

    def test_card_rebuild_with_supplied_pay(self):
        a,p,_=self.card_example()
        p['take_home_pay']='3280.00'
        for c in ('Income','Savings'):
            p['targets'][c]=self.plan['targets'][c]
        for k in ('buffer','buffer_goal','buffer_current'):
            p[k]=self.plan[k]
        v=funds.validate_plan(a,p)
        self.assertFalse(v['card_only'])
        self.assertTrue(v['supplied_income'])
        self.assertEqual(v['income'],Decimal('3280.00'))
        self.assertEqual(v['allocated'],Decimal('3280.00'))

    def test_double_charge_one_extra_and_no_yearly(self):
        for share in ('1','0.5'):
            for leak in self.plan['leaks']:
                if leak['kind']=='check':leak['share']=share
            checks=[l for l in self.validate()['leaks'] if l['what']=='Target twice']
            self.assertEqual(checks[0]['monthly'],Decimal('28.74'))
            self.assertIsNone(checks[0]['yearly'])
        self.build()
        line=next(l for l in (self.dir/'REPORT.md').read_text().splitlines() if l.startswith('| Target twice'))
        self.assertIn('$28.74 |  |',line)
        self.assertIn('9/18 Target, 9/18 Target',line)
        self.assertNotIn('S1:',line)
        with zipfile.ZipFile(self.dir/'Budget.xlsx') as z:
            tree=ET.fromstring(z.read('xl/worksheets/sheet4.xml'))
            for row in tree.findall('x:sheetData/x:row',NS):
                if 'Target twice' in ''.join(row.itertext()):
                    cells=list(row)
                    self.assertEqual(cells[1].find('x:v',NS).text,'28.74')
                    self.assertIsNone(cells[2].find('x:v',NS))

    def test_habits_cannot_be_overridden_or_omitted(self):
        v=self.validate()
        habits=[l for l in v['leaks'] if l['kind']=='habit']
        self.assertEqual([l['monthly'] for l in habits],[Decimal('305.03'),Decimal('54.55')])
        self.plan['leaks'].append({'what':'Coffee','lines':habits[1]['lines'],'share':'0.25','kind':'observed','action':'Cut'})
        with self.assertRaisesRegex(ValueError,'fixed at half'):
            self.validate()

    def test_full_list_plain_sources_and_large_summary(self):
        result=self.build()
        report=(self.dir/'REPORT.md').read_text()
        self.assertEqual(result['headlines'][1],'You pay for 13 monthly subscriptions: $170.85 a month ($2,050.20 a year).')
        for item in self.a['subscriptions']['items']:
            self.assertIn('| '+item['name']+' |',report)
        self.assertNotRegex(report,r'S\d+:\d+')
        self.assertNotIn('.;',report)
        with zipfile.ZipFile(self.dir/'Budget.xlsx') as z:
            tree=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(len(tree.findall('.//x:c[@s="6"]',NS)),4)
            self.assertEqual(len(tree.findall('.//x:c[@s="7"]',NS)),3)
            styles=ET.fromstring(z.read('xl/styles.xml'))
            self.assertEqual(styles.findall('x:fonts/x:font',NS)[3].find('x:sz',NS).get('val'),'20')
            sub=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
            self.assertEqual(sub.find('.//x:c[@r="D15"]/x:v',NS).text,'170.85')
            self.assertEqual(sub.find('.//x:c[@r="E15"]/x:v',NS).text,'2050.20')

    def test_reject_not_balanced(self):
        self.plan['targets']['Shopping']['amount']='211.00'
        with self.assertRaisesRegex(ValueError, 'does not add up.*1.00'):
            self.validate()

    def test_reject_more_than_half(self):
        self.plan['targets']['Groceries']['amount']='180.00'
        with self.assertRaisesRegex(ValueError, 'Groceries: cannot cut more than half'):
            self.validate()

    def test_reject_zero_flexible(self):
        self.plan['targets']['Groceries']['amount']='0.00'
        with self.assertRaisesRegex(ValueError, 'cannot be zero'):
            self.validate()

    def test_reject_missing_reason(self):
        self.plan['targets']['Shopping']['why']=''
        with self.assertRaisesRegex(ValueError, 'every cut needs a reason'):
            self.validate()

    def test_reject_changed_fixed_bill(self):
        self.plan['targets']['Housing']['amount']='900.00'
        with self.assertRaisesRegex(ValueError, 'fixed bill'):
            self.validate()

    def test_reject_changed_income(self):
        self.plan['targets']['Income']['amount']='3500.00'
        with self.assertRaisesRegex(ValueError, 'actually received'):
            self.validate()

    def test_reject_no_fun(self):
        self.plan['targets']['Entertainment']['amount']='0.00'
        with self.assertRaisesRegex(ValueError, 'guilt-free'):
            self.validate()

    def test_reject_savings_before_buffer(self):
        self.plan['buffer']='0.00'
        with self.assertRaisesRegex(ValueError, 'buffer first'):
            self.validate()

    def test_reject_double_counted_leaks(self):
        self.plan['leaks'].append(dict(next(l for l in self.plan['leaks'] if l['what']=='Audible')))
        with self.assertRaisesRegex(ValueError, 'double-count'):
            self.validate()

    def test_reject_invented_leak_line(self):
        self.plan['leaks'][0]['lines']=['S1:9999']
        with self.assertRaisesRegex(ValueError, 'existing source line'):
            self.validate()

    def test_reject_unexplained_subscription_cut(self):
        self.plan['leaks']=[l for l in self.plan['leaks'] if 'Hulu' not in l['what']]
        with self.assertRaisesRegex(ValueError, 'every removable charge cut'):
            self.validate()

    def test_reject_stale_analysis(self):
        self.a['categories']['Housing']='1.00'
        with self.assertRaisesRegex(ValueError, 'totals changed'):
            self.validate()

    def test_reject_float_nan_and_duplicate_json(self):
        for bad in (0.1,'NaN','1.001'):
            self.plan['targets']['Shopping']['amount']=bad
            with self.subTest(value=bad),self.assertRaises(ValueError):
                self.validate()
        p=self.dir/'duplicate.json'
        p.write_text('{"targets": {}, "targets": {}}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            funds.load_json(p)

    def test_xlsx_parts_order_dates_formula_cache_and_no_drift(self):
        self.build()
        with zipfile.ZipFile(self.dir/'Budget.xlsx') as z:
            for part in ['[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/styles.xml',
                         'xl/_rels/workbook.xml.rels'] + [f'xl/worksheets/sheet{i}.xml' for i in range(1,6)]:
                self.assertIn(part,z.namelist())
            for name in z.namelist():
                ET.fromstring(z.read(name))
                self.assertNotIn(b'NaN', z.read(name))
                self.assertNotIn(b'Infinity', z.read(name))
            workbook=ET.fromstring(z.read('xl/workbook.xml'))
            self.assertEqual([s.attrib['name'] for s in workbook.findall('x:sheets/x:sheet',NS)],
                             ['Summary','Subscriptions','Budget','Leaks','Every charge'])
            budget=ET.fromstring(z.read('xl/worksheets/sheet3.xml'))
            formula_cell=budget.find('.//x:c[@r="C25"]',NS)
            self.assertEqual(formula_cell.find('x:f',NS).text,'SUM(C2:C24)')
            self.assertEqual(formula_cell.find('x:v',NS).text,'3280.00')
            for el in budget.findall('.//x:c[x:f]',NS):
                self.assertIsNotNone(el.find('x:v',NS))
            charges=ET.fromstring(z.read('xl/worksheets/sheet5.xml'))
            self.assertIsNotNone(charges.find('x:autoFilter',NS))
            self.assertEqual(charges.find('.//x:pane',NS).attrib['ySplit'],'1')
            self.assertEqual(charges.find('.//x:c[@r="A2"]',NS).attrib['s'],'3')
            self.assertIsNone(charges.find('.//x:c[@r="A2"]',NS).get('t'))
            self.assertEqual(len(charges.findall('x:sheetData/x:row',NS)),99)
            styles=ET.fromstring(z.read('xl/styles.xml'))
            self.assertIn('$',styles.find('x:numFmts/x:numFmt',NS).attrib['formatCode'])

    def test_plain_report_same_headlines_and_notice(self):
        result=self.build()
        report=(self.dir/'REPORT.md').read_text()
        for line in result['headlines']:
            self.assertIn(line,report)
        self.assertTrue(report.startswith('SAMPLE STATEMENT, FICTIONAL PERSON'))
        self.assertIn('$79.71',report)
        self.assertIn('Target twice (check this)',report)

    def test_strings_cannot_be_formulas(self):
        output=self.dir/'literal.xlsx'
        make_xlsx.write_xlsx(output,[{'name':'Literal','widths':[30], 'rows':[['Header'],['=HYPERLINK("bad")'],['<bad>&"']]}])
        with zipfile.ZipFile(output) as z:
            tree=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(len(tree.findall('.//x:f',NS)),0)
            self.assertEqual(tree.find('.//x:c[@r="A2"]',NS).attrib['t'],'inlineStr')

    def test_libreoffice_budget_csv(self):
        binary=shutil.which('soffice')
        if not binary:
            self.skipTest('soffice not on PATH')
        self.build()
        output=self.dir/'converted'
        output.mkdir()
        # LibreOffice CSV option 12=-1 exports every worksheet separately.
        profile=self.dir/'lo-profile'
        command=[binary,'-env:UserInstallation='+profile.as_uri(),'--headless','--convert-to',
                 'csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true,false,false,-1',
                 '--outdir',str(output),str(self.dir/'Budget.xlsx')]
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=45)
        except subprocess.TimeoutExpired:
            self.fail('LibreOffice timed out while opening workbook')
        if result.returncode in (-6, 134):
            self.skipTest('Installed LibreOffice aborts under this sandbox (SIGABRT); native workbook validation unavailable')
        self.assertEqual(result.returncode,0,result.stderr)
        candidates=list(output.glob('*Budget*.csv'))
        self.assertTrue(candidates,'LibreOffice did not export the Budget sheet: '+result.stdout+result.stderr)
        rows=[]
        for path in candidates:
            rows.extend(csv.reader(io.StringIO(path.read_text())))
        totals=next((r for r in rows if r and r[0]=='Total assigned'),None)
        self.assertIsNotNone(totals)
        self.assertEqual(funds.money(totals[2]),Decimal('3280.00'))


class RequiredReviewTests(Workspace):
    def setUp(self):
        super().setUp()
        clean=self.dir/'card.csv'
        funds.normalize([ROOT/'tests/fixtures/card-review.csv'],clean)
        funds.reconcile(clean)
        kinds={'NETFLIX.COM':'video','HULU':'video','SPOTIFY USA':'music',
               'YOUTUBE PREMIUM':'music','NOOM':'fitness','CLOUD BACKUP ANNUAL':'software'}
        self.cats={key:{'category':'Subscriptions','name':'Noom' if key=='NOOM' else key,
                       'kind':kind,'billing':'unclear' if key=='NOOM' else 'yearly' if key=='CLOUD BACKUP ANNUAL' else 'monthly',
                       'where':'Original billing provider > Manage subscription'} for key,kind in kinds.items()}
        self.cats['INTEREST CHARGE']={'category':'Bank Fees & Interest','name':'Interest'}
        self.clean=clean
        self.a_path=self.dir/'analysis.json'
        self.analyze()
        self.p={'targets':{c:{'amount':self.a['categories'][c],'why':'Keep observed spending'}
                           for c in funds.CATEGORIES if c not in ('Income','Savings')},
                'fee_actions':{'interest':{'action':'Check the payoff amount and payment date.'}}, 'leaks':[]}
        for g in self.a['overlaps']:
            self.p['leaks'].append({'what':'Review '+g['id'], 'kind':'check', 'overlap':g['id'],
                'lines':g['lines'],'action':'Keep only the services you use.',
                'reason':'Different services may be useful; confirm preferences before canceling.'})

    def analyze(self):
        funds.save_json(self.dir/'cats.json',self.cats)
        funds.analyze(self.clean,self.dir/'cats.json',self.a_path)
        self.a=funds.load_json(self.a_path)

    def build(self):
        funds.save_json(self.dir/'plan.json',self.p)
        return funds.build(self.a_path,self.dir/'plan.json',self.dir/'Budget.xlsx',self.dir/'REPORT.md')

    def test_card_all_three_checks_end_to_end(self):
        result=self.build()
        self.assertEqual(result['headlines'][0],'You spent $451.47 on this card.')
        self.assertIn('4 monthly subscriptions: $61.00 a month ($732.00 a year)',result['headlines'][1])
        self.assertIn('1 yearly subscription: $10.00 a month',result['headlines'][1])
        self.assertEqual(result['subscriptions']['monthly'],'71.00')
        self.assertEqual(result['subscriptions']['yearly'],'852.00')
        self.assertEqual(result['subscriptions']['listed_count'],6)
        report=(self.dir/'REPORT.md').read_text()
        self.assertIn('plus $209.00 Noom, billing unclear: check it',report)
        self.assertIn('Interest charges (check this) | $61.47 |  |',report)
        self.assertIn('Pay the balance down or in full',report)
        self.assertIn('Next month’s interest may not be zero.',report)
        self.assertIn('Yearly, charge divided by 12',report)
        self.assertNotIn('$2,508.00',report)
        with zipfile.ZipFile(self.dir/'Budget.xlsx') as z:
            for sheet in (1,2):
                self.assertIn('plus $209.00 Noom, billing unclear: check it',z.read(f'xl/worksheets/sheet{sheet}.xml').decode())
            sub=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
            for row in sub.findall('x:sheetData/x:row',NS):
                if list(row)[0].find('x:is/x:t',NS) is not None and list(row)[0].find('x:is/x:t',NS).text=='Noom':
                    self.assertIsNone(list(row)[3].find('x:v',NS))
                    self.assertIsNone(list(row)[4].find('x:v',NS))
            self.assertEqual(sub.find('.//x:c[@r="D8"]/x:v',NS).text,'71.00')
            self.assertEqual(sub.find('.//x:c[@r="E8"]/x:v',NS).text,'852.00')

    def test_overlap_groups_found_in_card(self):
        groups={g['id']:set(g['merchants']) for g in self.a['overlaps']}
        self.assertEqual(groups,{'video':{'NETFLIX.COM','HULU'},'music':{'SPOTIFY USA','YOUTUBE PREMIUM'}})

    def test_missing_either_overlap_refuses_build(self):
        for kind in ('video','music'):
            original=copy.deepcopy(self.p)
            self.p['leaks']=[l for l in self.p['leaks'] if l['overlap']!=kind]
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError,'Overlap needs.*'+kind):
                self.build()
            self.p=original

    def test_overlap_check_requires_reason_and_all_members(self):
        for field,value in [('reason',''),('lines',[self.p['leaks'][0]['lines'][0]])]:
            p=copy.deepcopy(self.p)
            p['leaks'][0][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'every group line and a one-line reason'):
                funds.validate_plan(self.a,p)

    def test_overlap_can_cancel_one_keep_one(self):
        row=next(l for l in self.p['leaks'] if l['overlap']=='music')
        spotify=next(i for i in self.a['subscriptions']['items'] if i['merchant']=='SPOTIFY USA')
        row.update(kind='recurring',lines=spotify['lines'],keep='YOUTUBE PREMIUM',action='Keep YouTube Music and cancel Spotify.')
        self.p['targets']['Subscriptions']['amount']='377.00'
        v=funds.validate_plan(self.a,self.p)
        self.assertEqual(v['leakage'],Decimal('13.00'))
        row['keep']='SPOTIFY USA'
        with self.assertRaisesRegex(ValueError,'keep one service'):
            funds.validate_plan(self.a,self.p)

    def test_unknown_overlap_cannot_satisfy_review(self):
        self.p['leaks'][0]['overlap']='made-up'
        with self.assertRaisesRegex(ValueError,'Unknown or repeated overlap'):
            self.build()

    def test_removed_analysis_candidates_do_not_bypass_review(self):
        self.a['overlaps']=[]
        self.a['fee_leaks']=[]
        self.p['leaks']=[]
        with self.assertRaisesRegex(ValueError,'Overlap needs'):
            funds.validate_plan(self.a,self.p)
        self.p['fee_actions']={}
        with self.assertRaisesRegex(ValueError,'Every fee and interest'):
            funds.validate_plan(self.a,self.p)

    def test_missing_interest_action_refuses_build(self):
        self.p['fee_actions']={}
        with self.assertRaisesRegex(ValueError,'Every fee and interest.*interest'):
            self.build()

    def test_blank_fee_action_refused(self):
        self.p['fee_actions']['interest']['action']=' '
        with self.assertRaisesRegex(ValueError,'needs an action'):
            self.build()

    def test_interest_cannot_promise_recurring_savings(self):
        self.p['fee_actions']['interest']['kind']='observed'
        with self.assertRaisesRegex(ValueError,'interest must remain check'):
            self.build()
        self.p['fee_actions']['interest'].pop('kind')
        self.p['targets']['Bank Fees & Interest']['amount']='0.00'
        with self.assertRaisesRegex(ValueError,'every removable charge cut'):
            self.build()

    def test_unclear_cannot_be_annualized_as_a_leak(self):
        noom=next(i for i in self.a['subscriptions']['items'] if i['merchant']=='NOOM')
        self.p['leaks'].append({'what':'Noom','lines':noom['lines'],'kind':'recurring','action':'Cancel'})
        with self.assertRaisesRegex(ValueError,'Billing unclear'):
            self.build()

    def test_billing_and_kind_required(self):
        for field in ('billing','kind'):
            cats=copy.deepcopy(self.cats)
            del self.cats['HULU'][field]
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,field):
                self.analyze()
            self.cats=cats

    def test_bad_billing_and_kind_refused(self):
        for field,value in [('billing','monthly-estimate'),('kind','streaming')]:
            cats=copy.deepcopy(self.cats)
            self.cats['HULU'][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,field):
                self.analyze()
            self.cats=cats

    def test_large_charge_monthly_needs_confirmation(self):
        self.cats['NOOM']['billing']='monthly'
        with self.assertRaisesRegex(ValueError,'charge over .60'):
            self.analyze()
        self.cats['NOOM']['billing_reason']='The person confirmed this is their monthly plan.'
        self.analyze()
        self.assertEqual(self.a['subscriptions']['monthly_billed'],'270.00')

    def test_example_all_fees_and_bundle_overlaps(self):
        a=funds.load_json(self.analysis())
        groups={g['id']:g for g in a['overlaps']}
        self.assertEqual(set(groups),{'video','music','delivery pass','bundle:hulu'})
        self.assertIn('AMAZON PRIME',groups['video']['merchants'])
        self.assertEqual(set(groups['bundle:hulu']['merchants']),{'HULU','DISNEY PLUS BUNDLE'})
        p=funds.load_json(RUN/'work/plan.json')
        v=funds.validate_plan(a,p)
        fee_lines=set(a['fees']['lines'])
        covered=[i for l in v['leaks'] for i in l['lines'] if i in fee_lines]
        self.assertEqual(set(covered),fee_lines)
        self.assertEqual(len(covered),7)
        for group in a['fee_leaks']:
            bad=copy.deepcopy(p)
            del bad['fee_actions'][group['id']]
            with self.subTest(group=group['id']),self.assertRaisesRegex(ValueError,'Every fee and interest'):
                funds.validate_plan(a,bad)

    def test_yearly_rounding_preserves_actual_annual_cost(self):
        group={'merchant':'A','name':'Annual','total':Decimal('209'),'count':1,'lines':['S1:2']}
        subs=funds.subscription_summary([group],{'A':{'billing':'yearly','kind':'software'}})
        self.assertEqual(subs['monthly'],Decimal('17.42'))
        self.assertEqual(subs['yearly'],Decimal('209.00'))
        self.assertEqual(subs['items'][0]['yearly'],Decimal('209.00'))

    def test_yearly_charge_not_repeated_as_monthly_leak(self):
        annual=next(i for i in self.a['subscriptions']['items'] if i['billing']=='yearly')
        self.p['leaks'].append({'what':'Annual backup','lines':annual['lines'],'kind':'recurring','action':'Cancel'})
        with self.assertRaisesRegex(ValueError,'Billing unclear or yearly'):
            self.build()

    def test_youtube_music_included_even_if_labeled_video(self):
        self.cats['YOUTUBE PREMIUM']['kind']='video'
        self.analyze()
        music=next(g for g in self.a['overlaps'] if g['id']=='music')
        self.assertEqual(set(music['merchants']),{'SPOTIFY USA','YOUTUBE PREMIUM'})

    def test_fee_candidates_include_all_types_and_unknown_bank_fee(self):
        descriptions=['OVERDRAFT FEE','NSF FEE','ATM OPERATOR FEE','MONTHLY MAINTENANCE',
                      'LATE FEE','FOREIGN TRANSACTION FEE','PURCHASE INTEREST','SPECIAL CHARGE']
        rows=[{'id':str(i),'description':d,'category':'Bank Fees & Interest','amount':Decimal('-1.23')}
              for i,d in enumerate(descriptions)]
        groups=funds.fee_candidates(rows)
        self.assertEqual({i for g in groups for i in g['lines']},{str(i) for i in range(8)})
        self.assertEqual(sum(g['monthly'] for g in groups),Decimal('9.84'))
        self.assertEqual(next(g for g in groups if g['id']=='interest')['kind'],'check')

    def test_monthly_interest_history_not_a_subscription(self):
        raw=self.dir/'interest.csv'
        raw.write_text('Date,Description,Amount\n8/1/26,INTEREST CHARGE,-10\n9/1/26,INTEREST CHARGE,-10\n')
        clean=self.dir/'interest-clean.csv'
        funds.normalize([raw],clean)
        funds.reconcile(clean)
        funds.save_json(self.dir/'interest-cats.json',{'INTEREST CHARGE':{'category':'Bank Fees & Interest','name':'Interest'}})
        a=funds.analyze(clean,self.dir/'interest-cats.json',self.dir/'interest-analysis.json','2026-09')
        self.assertEqual(a['subscriptions']['listed_count'],0)
        self.assertEqual(a['fee_leaks'][0]['monthly'],Decimal('10.00'))

    def test_old_analysis_cannot_bypass_new_checks(self):
        self.a['schema']=1
        with self.assertRaisesRegex(ValueError,'Rerun analyze'):
            funds.validate_plan(self.a,self.p)


class PackageTests(Workspace):
    def test_no_network_code(self):
        for path in SCRIPTS.glob('*.py'):
            source=path.read_text()
            for forbidden in ('urllib','http.client','socket','requests'):
                self.assertNotIn(forbidden,source,str(path))

    def test_skill_frontmatter_and_categories(self):
        skill=(SCRIPTS.parent/'SKILL.md').read_text()
        head=skill.split('---',2)[1]
        self.assertIn('name: insufficient-funds',head)
        desc=next(l for l in head.splitlines() if l.startswith('description: ')).split(': ',1)[1]
        self.assertLess(len(desc),1024)
        self.assertLessEqual(len(skill.split()),1300)
        guide=(SCRIPTS.parent/'categories.md').read_text()
        for c in funds.CATEGORIES:
            self.assertIn('- '+c+':',guide)
        self.assertLess(len(guide.split()),370)

    def test_manifests_and_install_names(self):
        plugin=funds.load_json(ROOT/'.claude-plugin/plugin.json')
        market=funds.load_json(ROOT/'.claude-plugin/marketplace.json')
        self.assertEqual(plugin['name'],'insufficient-funds')
        self.assertEqual(market['name'],plugin['name'])
        self.assertEqual(market['plugins'][0]['name'],plugin['name'])
        readme=(ROOT/'README.md').read_text()
        self.assertIn('/plugin marketplace add JoeBrunner/'+market['name'],readme)
        self.assertIn('/plugin install '+plugin['name']+'@'+market['name'],readme)
        self.assertNotIn('—',readme)
        self.assertIn('[PROOF.md](PROOF.md)',readme)

    def test_zip_reproducible_exact_contents(self):
        spec=importlib.util.spec_from_file_location('package_zip',ROOT/'make_zip.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        a,b=self.dir/'a.zip',self.dir/'b.zip'
        module.build(a)
        module.build(b)
        self.assertEqual(a.read_bytes(),b.read_bytes())
        with zipfile.ZipFile(a) as z:
            self.assertEqual(set(z.namelist()),{'insufficient-funds/'+n for n in module.FILES})
            for name in z.namelist():
                self.assertEqual(z.read(name),(ROOT/'skills'/name).read_bytes())

    def test_example_generator_deterministic_and_story(self):
        spec=importlib.util.spec_from_file_location('make_statement',ROOT/'examples/make_statement.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.table(),module.table())
        negative=[r for r in KEY['transactions'] if Decimal(r['balance'])<0]
        self.assertGreaterEqual(negative[0]['date'],'2026-09-25')
        self.assertLess(Decimal(KEY['summary']['closing']),0)
        self.assertGreater(Decimal(KEY['spending']),Decimal(KEY['income']))
        self.assertEqual(next(csv.reader(io.StringIO(SAMPLE.read_text())))[0], 'SAMPLE STATEMENT, FICTIONAL PERSON')

    def test_pdf_text_contains_every_transaction_amount(self):
        binary=shutil.which('pdftotext')
        if not binary:
            self.skipTest('pdftotext not on PATH')
        pdf=ROOT/'examples/statement-2026-09.pdf'
        if not pdf.exists():
            self.skipTest('Example PDF unavailable: LibreOffice conversion blocked; printable HTML supplied')
        result=subprocess.run([binary,'-layout',str(pdf),'-'],capture_output=True,text=True,check=True)
        text=result.stdout
        self.assertIn('SAMPLE STATEMENT',text)
        # Count repeated amounts, not merely whether one instance exists.
        needed={}
        for row in KEY['transactions']:
            needed[row['amount']]=needed.get(row['amount'],0)+1
        for amount,count in needed.items():
            occurrences=len(re.findall(r'(?<![\d.])'+re.escape(amount)+r'(?![\d.])',text))
            self.assertGreaterEqual(occurrences,count,amount)


if __name__=='__main__':
    unittest.main()
