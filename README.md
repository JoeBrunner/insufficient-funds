# Insufficient Funds

You get paid, and by the end of the month you don't know where it went. Give Claude your bank statement, and it reads every line, finds the leaks, and hands back a budget spreadsheet built from your real numbers.

Free, MIT, no signup, no API key, nothing to connect, no bank login.

## Install

**Claude Code.** Paste this into Claude Code:

```text
https://github.com/JoeBrunner/insufficient-funds

install the skill
```

Or run these two lines in Claude Code:

```text
/plugin marketplace add JoeBrunner/insufficient-funds
/plugin install insufficient-funds@insufficient-funds
```

**The Claude app** (claude.ai or the desktop app). Download
[insufficient-funds.zip](https://github.com/JoeBrunner/insufficient-funds/raw/main/insufficient-funds.zip).
In Claude, open **Customize > Skills**, click **+**, then **Create skill > Upload a skill**, and choose the zip.
Turn on **Code execution and file creation** in **Settings > Capabilities**. Menu names may vary by app version and plan.

**Copy the folder**, if you prefer:

```bash
git clone https://github.com/JoeBrunner/insufficient-funds.git
cp -r insufficient-funds/skills/insufficient-funds ~/.claude/skills/
```

### Notes for Claude, if you're installing this for someone

Install the Claude Code plugin when someone pastes this link and asks you to install the skill:

```bash
claude plugin marketplace add JoeBrunner/insufficient-funds
claude plugin install insufficient-funds@insufficient-funds
```

This plugin contains one skill, a category guide, and two Python scripts. It has no hooks, account connection, network code or third-party dependencies. It needs Python 3.9 or newer. Tell them what you installed, to run `/reload-plugins` or restart Claude Code, and to share a statement with their spending question. Uninstall with `claude plugin uninstall insufficient-funds@insufficient-funds`.

If the `claude` command is unavailable, copy `skills/insufficient-funds` into `~/.claude/skills/` when that is their requested setup. For the regular app, give them the zip and the upload steps above. Do not install anything into their bank account or ask for a password. Read statements only after the person supplies them.

## Use it

```text
Where did my money go? Build me a budget from this statement.
```

Attach the file, or give Claude Code its path. In your bank's website or app, look for **Statements** or **Download transactions**, select the last full month, and choose **CSV**. If there is no CSV option, download the statement PDF instead. Include its summary and every page. Pasted statement text works too.

Claude sorts the charges and decides what to change. Python adds everything up and checks it to the cent. If the transactions do not match the statement, it stops and explains what is missing. A CSV without balances or summary totals still gets the full result, clearly marked unverified. Paste the statement summary later and Claude can check it.

## What you get

**Budget.xlsx**, with five tabs:

| Tab | What's in it |
|---|---|
| Summary | Four plain headlines, the key numbers and whether the file could be checked |
| Subscriptions | Every recurring charge and membership, including the gym, with its cost, billing interval and cancellation route |
| Budget | Last month's spending, next month's targets, and why each change makes sense |
| Leaks | Subscriptions to review, fees, habits and possible duplicate charges, with the source lines |
| Every charge | Every transaction, its category and flags, with a frozen header and filter |

You also get **REPORT.md**, the same story in plain text. The spreadsheet uses the standard Excel format for Excel, Numbers and Google Sheets. Currency, dates and cached formula totals are included so previews can display the numbers. Cross-app testing limits are recorded with the example.

Every overlap group gets a cancellation choice or a reason to check it. Every fee and interest charge appears, including interest that may take time to reduce. Monthly subscription totals exclude unclear billing. Yearly plans show a labeled monthly equivalent; a large unfamiliar charge stays separate until its billing is confirmed.

Fixed bills stay put. Flexible spending drops by at most half in one month, and a full budget always keeps guilt-free fun money. Habit leak estimates are consistently half of the month’s delivery and small daily purchases, rounded down to cents. Whatever is left in a full budget goes to a buffer first, then savings. If the numbers cannot support that budget, Claude says so. Tell it "keep Hulu" or change another assumption and it rebuilds the files.

In Claude Code, each run goes in `insufficient-funds/YYYY-MM/` in your current folder. In the app, Claude gives you download links. To change the budget, ask Claude to rebuild it so the checks and headlines update too.

## Your statement stays yours

The Python scripts run on your computer in Claude Code, or in Claude's sandbox in the regular app. They make no network calls and do not copy the original statement. They save the cleaned transactions, working files and results only inside the run folder. The spreadsheet and report contain financial details, so share them deliberately.

Claude still receives whatever you share in the conversation, under your Claude account's data settings. This skill cannot change those settings or promise how Claude retains uploads. You can remove account and card numbers before sharing; the skill also masks likely numbers in descriptions and leaves account-number columns out of the outputs.

## Good to know

- This is a second look at your own numbers, not financial advice.
- It can only see what's on the statement. A subscription charge does not prove you don't use it, and a repeated charge is something to check, not proof you were overcharged.
- Transfers, card payments and refunds are handled separately from paychecks. A card-only statement still gets subscriptions, leaks and next month’s spending targets. It has no savings or buffer allocation until you supply take-home pay for a full budget. Card payments never count as income.
- Proposed cancellations and fee avoidance are assumptions you can change. Yearly leak figures are the monthly scenario times twelve, not a promise. Monthly totals also cannot guarantee that bills fall after payday.
- CSV layouts vary. Common U.S. checking/card layouts are tested; unusual exports may need Claude to identify the columns. Current price and layout research is in the example's source notes.
- A run uses some of your Claude plan's usage. The skill itself is free.
- Not made by or affiliated with Anthropic.

## The example

**SAMPLE STATEMENT, FICTIONAL PERSON.** Alex is a made-up 27-year-old renter in Raleigh with a checking account at the made-up Cedar Kite Bank. September 2026 includes paychecks, rent, groceries, coffee, delivery, subscriptions, a repeated Target charge and bank fees. No real person's financial records are used.

Try the [CSV](examples/statement-2026-09.csv), [PDF](examples/statement-2026-09.pdf) or [printable HTML](examples/statement-2026-09.html). The [example notes](examples/README.md) explain the prices and assumptions. The [developer sample](examples/sample-run/REPORT.md) and [spreadsheet](examples/sample-run/Budget.xlsx) show the arithmetic and output format. They are not a real-world Claude proof.

### What it found on Alex's September

Real runs, October 15, 2026, in Claude Code and the Claude app, on the statement above:

- You brought in $3,280.00. You spent $3,760.35. That's $480.35 more than you made.
- You pay for 13 subscriptions: $170.85 a month ($2,050.20 a year).
- $469.55 a month is leaking ($5,634.60 a year): delivery, overdraft fees and daily coffee lead.
- The budget frees about $550 a month: enough to close the gap and start a buffer.

It found every problem planted in the statement, read the PDF to the same totals, and handled a credit card file it had
never seen. Full results, what failed along the way and the limits: [PROOF.md](PROOF.md). Transcripts:
[Claude Code](examples/run-claude-code.md) and [the Claude app](examples/run-claude-app.md). The developer sample is
separate from those real runs.

## Tests

```bash
python3 -m unittest discover -s tests
python3 make_zip.py
```

Tests use only Python's standard library. If LibreOffice or PDF text extraction cannot run, the relevant checks say why they were skipped. The app zip includes only the skill and its runtime files, never the examples or answer key.

## License

MIT. See [LICENSE](LICENSE).
