# A real run in the Claude app

Fictional sample only: `examples/statement-2026-09.csv` (Alex Mercer, Cedar Kite Bank, both made up). Run 2026-10-15 on
claude.ai with the skill uploaded as `insufficient-funds.zip` (Customize > Skills > Add > Upload skill), Opus 5.5,
Medium. New chat, the CSV attached, this message:

> I get paid every two weeks and by the end of the month I have no idea where it went. Here's my September bank
> statement. Where did my money go?

About 3 minutes, 8 commands in the app's sandbox. It handed back `Budget.xlsx` (downloaded and opened: five tabs,
same numbers as the chat; copy in `proof/2026-10-15-claude-app/`) and `REPORT.md`. Claude's reply, as shown in the chat:

---

One flag first: this file is marked "SAMPLE STATEMENT, FICTIONAL PERSON" (Raleigh, NC, with a paycheck from Cedar Lane
Design). If it isn't actually your account, send me your real September export and I'll run it the same way. The
analysis below covers exactly what's in this file. Every line matched the bank's opening balance, closing balance and
totals to the cent.

**Headlines**

- You brought in $3,280.00. You spent $3,760.35. That's $480.35 more than you made.
- You pay for 13 monthly subscriptions: $170.85 a month ($2,050.20 a year).
- $469.55 a month is leaking ($5,634.60 a year). Top leaks: Delivery (18 orders), Overdraft and NSF fees, and Starbucks
  (22 visits).
- This budget frees $549.47 a month.

**Where it went.** Delivery is the biggest piece by far: $610 across 18 DoorDash and Uber Eats orders, roughly four a
week. That's more than you spent on groceries ($368). After that comes Amazon and Target at $327, subscriptions at $171,
and restaurants and coffee at $192, which includes Starbucks almost every weekday ($109). Bank fees added another $90.

**Why it feels like it vanishes.** Each paycheck gets hit right away by a big bill. Rent ($975) comes out the day after
the first paycheck. The loans and insurance ($507) come out in the three days after the second. The small daily charges
then drain whatever's left. You hit $2.52 on Sep 17, the day before payday, and went overdrawn on Sep 29. That one
overdraft cost $65 in fees, and you ended the month $125.35 below zero.

**Every subscription**

| Subscription | Monthly | Cancel at |
|---|---:|---|
| ChatGPT Plus | $20.00 | ChatGPT > Settings > Subscription |
| Netflix | $19.99 | Netflix > Account |
| YouTube Premium | $15.99 | youtube.com/paid_memberships |
| Planet Fitness | $15.00 | Home club, in person or certified letter |
| Amazon Prime | $14.99 | Amazon > Account > Prime |
| Audible | $14.95 | audible.com > Account details |
| Disney+ Bundle | $12.99 | Disney+ > Account > Subscription |
| Spotify | $12.99 | spotify.com > Account > Manage plan |
| Hulu | $11.99 | Hulu > Account, or the original biller |
| DoorDash DashPass | $9.99 | DoorDash app > Manage DashPass |
| Uber One | $9.99 | Uber app > Uber One > Manage |
| Paramount+ | $8.99 | paramountplus.com > Account |
| Apple (unidentified) | $2.99 | iPhone Settings > your name > Subscriptions |

**What the plan cuts**

- Delivery: order half as often. That's $305 a month, and groceries go up $32 to cover the meals at home.
- Starbucks: half as many visits saves $54.55.
- Shopping: Amazon and Target go from $327 to $200.
- Subscriptions: cancel three of them. DashPass, because you have Uber One, which also covers your rides. Spotify,
  because YouTube Premium includes YouTube Music. Paramount+.
- Fees: use your own bank's ATMs or get cash back at checkout, which avoids the ATM fees. A small buffer plus a
  low-balance alert should prevent overdrafts.

**Things to check (not counted as savings)**

- Hulu: it's billed on its own, but your Disney bundle may already include it. If it does, the standalone Hulu is
  paying twice.
- Target: two identical $28.74 charges on Sep 18. If that was one purchase, dispute the second.
- The $85 online payment: it was attempted Sep 28 and bounced. Whatever bill that was is probably still unpaid, so
  check it before a late fee lands.
- Maintenance fee: ask the bank what waives the $12 monthly fee.
- Other subscriptions: keep Audible only if you use the credit each month. Look up what the $2.99 Apple charge is.

**Next month's budget.** All fixed bills stay where they are. After the cuts, $69.12 is left over for the buffer. That
isn't enough to get you back above zero yet: after covering the $125.35 overdraft, the buffer would still sit at
-$56.23. Getting to a $500 cushion will take a few months of this plan, or a couple of bigger cuts, such as rotating
streaming services instead of keeping six.

This is a second look at your own numbers, not financial advice.

*Budget (Spreadsheet, XLSX) · Report (Document, MD)*
