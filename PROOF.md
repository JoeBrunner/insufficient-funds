# Proof

Every claim the README and the reel make, tested for real on 2026-10-15. All statements are made up (a fictional
person, a fictional bank, real merchants at real prices). Each run started in an empty folder holding only the
statement; no run ever saw an answer key.

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | Installs fresh in Claude Code | **Pass.** Loaded from this repo with `claude -p --plugin-dir`, 9 runs across 3 rounds | `proof/2026-10-15-round-*/` |
| 2 | Works in the regular Claude app | **Pass.** Zip uploaded under Customize > Skills, new chat, CSV attached; about 3 minutes; handed back `Budget.xlsx` and `REPORT.md` | `examples/run-claude-app.md`, `proof/2026-10-15-claude-app/` |
| 3 | Reads a bank CSV and checks it to the cent | **Pass.** 98 lines; opening $295.00, deposits $3,425.00, withdrawals $3,845.35, closing -$125.35 all match | every CSV run |
| 4 | Reads the PDF and gets the same answer | **Pass.** Same money in and out, same leak total ($469.55) as the CSV. One difference: the PDF run counted 12 subscriptions ($167.86) where the CSV runs counted 13 ($170.85), because it judged a $2.99 Apple charge "unclear" | `proof/2026-10-15-round-3/pdf/` |
| 5 | Reads a card export it never saw | **Pass.** A second made-up person's credit card (Debit and Credit columns, no balance), written by Claude after the build: spending $1,772.07, right to the cent (the $150 payment kept out, the $22.99 refund netted). It says once that a file with no balance can't be checked and asks for the statement's summary box | `proof/cold/`, `proof/2026-10-15-round-3/cold/` |
| 6 | Sorts every charge | **Pass.** 98 of 98 and 64 of 64 lines categorized; the script refuses to go on otherwise | `work/categories.json` in each run |
| 7 | Finds the leaks | **Pass.** Bank statement: all 10 planted problems surfaced (Hulu inside a bundle, two music services, two delivery passes, a forgotten Audible, a trial that turned into Paramount+, a double charge, 7 fee lines, 18 delivery orders, 22 coffees, 13 subscriptions). Card: all 9 (four streaming services, a $209 Noom charge, a double charge, late fee, $61.47 interest, foreign fee, 12 deliveries, 14 coffees; the Apple Music overlap shows as "check this", since the statement only says Apple) | `tests/fixtures/answer-key.json`, `proof/cold/cold-answer-key.json` |
| 8 | The before and after | **Pass.** You brought in $3,280.00 and spent $3,760.35 ($480.35 short). 13 subscriptions, $170.85 a month ($2,050.20 a year). $469.55 a month leaking ($5,634.60 a year). The budget frees $549.47 to $584.97 a month (Claude sets the targets, so this one moves by about $35 between runs; every other number above was identical in every run) | round 3 and the app run |
| 9 | Hands back a spreadsheet that opens | **Pass.** Five tabs (Summary, Subscriptions, Budget, Leaks, Every charge); opened in LibreOffice and macOS Quick Look; the app's download opened the same | `proof/2026-10-15-claude-app/Budget.xlsx` |
| 10 | Free, no API key, no bank login | **Pass.** Nothing to connect. A Claude Code run took 1.5 to 2.9 minutes, $0.70 to $0.83 at API list price (on a Claude plan it uses plan usage instead); the app took about 3 minutes | `examples/run-claude-code.md` |
| 11 | Your statement stays yours | **Pass.** The scripts contain no network code (a test fails if any appears); account numbers are masked to the last 4 | `tests/test_funds.py` |

## What changed because of the runs

- Round 1: a card file with no balance stopped the run; card-only statements got no plan; subscriptions were counted but
  not listed (so a forgotten Audible never reached the person); a double charge counted both charges; three runs gave
  three different leak totals. All fixed: habit leaks are now half of the month by code, so runs agree.
- Round 2: one run missed two music services, another left out $61.47 of interest, and a $209 one-off was counted as
  monthly. Fixed: code finds overlapping subscriptions and every fee line, and only monthly bills go in the
  subscription total.
- Round 3 and the app run: everything above passes.

## Limits, said plainly

- It sees only the statement. It can't tell whether you use a subscription, which app a bare "Apple" charge is, or
  whether a trial ended, so those are marked "check this" and never counted as savings.
- A file with no balance or summary can't be checked to the cent; it says so and asks for the summary box.
- "This budget frees" depends on the targets Claude sets, so two runs differ a little. The other headline numbers come
  from the script and match every time.
- It's a second look at your own numbers, not financial advice.
