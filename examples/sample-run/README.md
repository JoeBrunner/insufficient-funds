SAMPLE STATEMENT, FICTIONAL PERSON. Developer demonstration, not a real Claude proof run.

# Sample run

The categories and plan in `work/` were written for the fictional statement. The production CLI generated the normalized transactions, reconciliation record, merchant groups, analysis, workbook and report. The future blind Claude runs must receive only the statement and installed skill, not this plan or the answer key.

| Result | Amount |
|---|---:|
| Regular income | $3,280.00 |
| Spending after reversals, excluding transfers | $3,760.35 |
| Monthly shortfall | $480.35 |
| All 13 subscriptions and memberships per month | $170.85 |
| Subscriptions per year | $2,050.20 |
| Proposed leak cuts per month | $508.49 |
| Same cuts repeated for twelve months | $6,101.88 |
| Total monthly spending reduction | $685.41 |
| Next month's buffer allocation | $205.06 |
| Starting balance | -$125.35 |
| Buffer after restoring the negative balance | $79.71 |

The account's full inflows are $3,425.00 and outflows are $3,845.35. Those include the roommate reimbursement and returned-payment reversal, which are not regular income. Opening balance $295.00 plus inflows less outflows equals the closing balance of -$125.35. All 98 running balances also reconcile. First negative balance: September 28, at the returned-payment attempt. The next day's grocery charge takes the account negative again before the overdraft fee.

Leak dollars are proposed avoidable spending, not all subscription costs. The Target duplicate is a check-only item and does not fund the plan. The buffer goal, cancellation choices and fee-avoidance assumptions are listed in `work/plan.json` and the report. The plan flags the returned payment's underlying obligation for confirmation.

## Commands actually run

From the repository root:

```bash
python3 skills/insufficient-funds/scripts/funds.py normalize examples/statement-2026-09.csv -o examples/sample-run/work/transactions.csv
python3 skills/insufficient-funds/scripts/funds.py reconcile examples/sample-run/work/transactions.csv --opening 295.00 --closing=-125.35 --deposits 3425.00 --withdrawals 3845.35
python3 skills/insufficient-funds/scripts/funds.py merchants examples/sample-run/work/transactions.csv -o examples/sample-run/work/merchants.json
# Categories were then written from the merchant groups.
python3 skills/insufficient-funds/scripts/funds.py analyze examples/sample-run/work/transactions.csv --categories examples/sample-run/work/categories.json -o examples/sample-run/work/analysis.json
# Targets, leak evidence and assumptions were then written in plan.json.
python3 skills/insufficient-funds/scripts/funds.py build examples/sample-run/work/analysis.json examples/sample-run/work/plan.json -o examples/sample-run/Budget.xlsx --report examples/sample-run/REPORT.md
python3 -m unittest discover -s tests
python3 make_zip.py
shasum -a 256 insufficient-funds.zip
python3 make_zip.py
shasum -a 256 insufficient-funds.zip
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
```

## Fix-round 2 verification on October 15, 2026

- Standard-library suite: **105 tests run, 104 passed, 1 skipped**. No failures. New coverage requires kind/billing labels, review of every overlap (including bundled services), automatic coverage and actions for all fees and interest, and exclusion of unclear charges from subscription totals. A small fictional card fixture checks two video services, two music services, $61.47 interest, a $209 Noom charge with unclear billing, and a yearly plan. Existing reconciliation, budget, privacy, packaging and workbook checks still pass.
- The manual CLI flow above completed. All 98 rows reconcile against the running balances and the four statement summary controls. Budget targets total exactly $3,280.00.
- Both installed Claude Code manifest commands returned **Validation passed**. They validate packaging, not real Claude execution behavior.
- Two root zip builds had identical SHA-256: `ebb231521a39a6a0d14be07c21b13e4e4b07b8887c7f70f3824141c7afc19621`. Exactly four runtime files, with no test key, examples, caches or stray files.
- Both runtime scripts parse using Python 3.9 syntax rules. Tests ran on the installed Python, not on separate Mac/Windows Python 3.9 machines.
- Every workbook XML part parses. Tests check Summary, Subscriptions, Budget, Leaks and Every charge in that order, four large headline cells, cached SUM totals, currency styles, real dates, frozen charge headers and autofilter.
- LibreOffice exists on PATH but workbook-to-CSV conversion aborts with SIGABRT (exit -6) inside this sandbox. This is the sole skipped test. Claude reported that it works outside the sandbox. No native spreadsheet opening or visual layout pass is claimed for this revision.
- The preserved PDF has four pages and all 98 transaction rows in its text layer. The `pdftotext` transaction-amount test passes. SHA-256 checks confirm that both Claude's PDF and `make_statement.py` are unchanged.
- SKILL.md is 1,287 words including frontmatter. The runtime still uses only the standard library and has no network code.
- `git diff --check` is clean. No commit, push, plugin installation or publication was performed.

Delivery's automatic half-cost cut is $305.03. Coffee's is $54.55: half of an odd number of cents rounds down so the cut never exceeds 50%. The $28.74 Target check is excluded from recurring savings and has no yearly figure. Subscription totals include the $15.00 gym membership even though its budget category is Health & Fitness.

The sample now records video, music, delivery-pass and Disney/Hulu overlap reviews. Amazon Prime counts in video; YouTube Premium counts in music even when its primary kind is video. Code supplies all seven fee lines and requires an action for each fee group. The existing cancellation choices and headline amounts are unchanged. This saved developer plan produces $508.49 of proposed monthly cuts; it is separate from Claude's $468.55 real-run result.

The small card fixture spends $451.47. Its four monthly subscriptions total $61.00, plus $10.00 per month for a $120 yearly plan. The known monthly equivalent is $71.00 and the yearly total is $852.00. Noom's $209 stays visible with unclear billing and no monthly/yearly estimate. Interest stays visible as a $61.47 check with no promised savings. Annual totals retain the original yearly charge even when dividing it by twelve requires rounding cents.

Billing labels replace the earlier frequency field. Charges above $60 need unclear billing or an explicit confirmation reason before being treated as monthly. Old analysis files must be regenerated; build refuses the earlier schema so these checks cannot silently be skipped.

This revision's sample is a developer demonstration. The existing real-run proof files are unchanged; fresh Claude Code and Claude app proof runs were not repeated. Price and export-layout evidence remains in `../sources.md`.
