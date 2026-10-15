SAMPLE STATEMENT, FICTIONAL PERSON.

# September 2026 example

Alex Mercer, age 27, rents in Raleigh. Alex, Cedar Kite Bank, the employer, account and transaction history are invented. Real merchant names and sourced subscription list prices make the month recognizable. The account is shown only as `****4417`.

`make_statement.py` uses one annotated data table and seed 202609 to generate the CSV, printable HTML and test answer key. It does not use the production normalizer or analyzer to calculate expected answers. The CSV uses the Date, Description, Amount, Running Bal. layout with a summary preamble. Its deposits include a roommate reimbursement and a reversed payment, so bank inflows differ from regular income. Taxes are not modeled; subscription entries use the listed monthly prices. Gym startup/annual fees are assumed to fall outside this month.

`statement-2026-09.pdf` is the same month printed the way a bank prints it: four pages, all 98 lines in its text layer. `python3 examples/make_statement.py --pdf` rebuilds it where LibreOffice is installed.

The account goes below zero late in the month. An attempted payment is reversed and a separate NSF fee appears. The sample budget labels the remaining obligation as something to confirm. The invented maintenance fee is assumed waivable, but no such terms are claimed for a real bank.

The answer key includes hidden fictional facts: an unused Audible subscription, a Paramount+ promotional trial that expired, and iCloud+ behind Apple billing. A successful honest run should flag those to check, not claim it can know the backstory from a statement. The key is in `tests/fixtures/answer-key.json` and excluded from the app zip. Do not give it to Claude during proof runs.

`sample-run/` is a developer demonstration of the full command flow. Its categories and plan were written for this fictional statement. It is not a blind evaluation and not a real Claude Code/app transcript. Every file in that folder contains fictional sample data. The real runs are in `run-claude-code.md`, `run-claude-app.md` and `../PROOF.md`.

See [source notes](sources.md) for current-price checks and CSV layout evidence.
