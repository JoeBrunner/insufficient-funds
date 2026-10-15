SAMPLE STATEMENT, FICTIONAL PERSON. Research checked October 15, 2026.

# Example sources and limits

These are example list prices, not personalized quotes. Promotions, taxes, billing partners and location can change an actual charge. September 2026 is the fictional statement period. The following plan prices were the public evidence available during this build; live signup was not completed.

| Service and plan | Monthly USD | Evidence |
|---|---:|---|
| Netflix Standard | 19.99 | [Netflix plans and pricing](https://help.netflix.com/en/node/24926?ref_type=adv), U.S. search-indexed price; the general help page can default to another country |
| Hulu with ads | 11.99 | [Hulu welcome page](https://www.hulu.com/welcome), regular standalone price in bundle terms |
| Disney+ and Hulu bundle, with ads | 12.99 | [Disney help, U.S. bundle plans](https://help.disneyplus.com/en-GB/article/disneyplus-en-ae-price), includes both services; help URLs and localized pages can redirect |
| Spotify Premium Individual | 12.99 | [Spotify U.S. Premium](https://www.spotify.com/us/premium/) |
| YouTube Premium Individual | 15.99 | [April 10, 2026 price report](https://www.macrumors.com/2026/04/10/youtube-premium-price-increase/); direct price verification was unavailable: public page returned a shell, then browser permission was denied. This row is secondary-source verified only |
| Apple iCloud+ 200 GB | 2.99 | [Apple U.S. pricing](https://support.apple.com/en-us/108047), United States row |
| Amazon Prime monthly | 14.99 | [Amazon membership cost](https://www.aboutamazon.com/news/retail/is-cost-of-prime-membership-worth-it) |
| Planet Fitness Classic | 15.00 | [Planet Fitness memberships](https://www.planetfitness.com/gym-memberships), advertised starting monthly price; location/annual/startup fees vary |
| DoorDash DashPass monthly | 9.99 | [DoorDash membership FAQ](https://help.doordash.com/consumers/s/article/T-Mobile-Partnership-FAQs), regular monthly price |
| Uber One monthly | 9.99 | [Uber One U.S.](https://www.uber.com/us/en/uber-one/) |
| Audible Premium Plus | 14.95 | [Audible membership terms](https://www.audible.com/ep/xfinity-membership), recurring full price after offer |
| ChatGPT Plus | 20.00 | [OpenAI Plus help](https://help.openai.com/en/articles/6950777-chatgpt-plus-) |
| Paramount+ Essential | 8.99 | [Paramount+ signup](https://www.paramountplus.com/account/signup/createaccount/); the promotional trial is fictional backstory, not an asserted current public trial offer |

An exact-phrase web search for "Cedar Kite Bank" found no matching bank. That supports using it as a clearly labeled invented name, not a legal uniqueness guarantee. No real bank's branding, routing number or customer account appears in the example.

## CSV layouts

Banks do not all publish versioned consumer CSV specifications. No live bank account was accessed. The reader tests the layouts below, identifies headers rather than bank names, and stops for mappings or reconciliation when it cannot establish the result. "Supported layout" does not promise that every current account export is identical.

| Layout | Header evidence and interpretation |
|---|---|
| Bank of America-style checking | `Date,Description,Amount,Running Bal.` and a summary preamble. [Primary converter implementation](https://gist.github.com/jeanralphaviles/75991cacec2cb8fa38ffa5c7454511e2) documents the fields; [Beancount's converter](https://beancount.io/tools/csv-to-beancount/bank-of-america) discusses running balances. Signed amounts |
| Chase checking | `Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #`. [Importer author's discussion](https://groups.google.com/g/beancount/c/N5fCig2YZck). Details distinguishes debit/credit; posting date wins |
| Chase card | `Transaction Date,Post Date,Description,Category,Type,Amount`. Signed amounts and Sale/Return directions; the exact current consumer headers were not independently verified with a bank-issued sample. Tested explicitly |
| Capital One card | `Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit`. Debit/credit columns are tested. Bank-published consumer header documentation was unavailable; this header set was found during export research, not a verified live account export |
| American Express expanded export | `Date,Description,Amount,Extended Details,Appears On Your Statement As,Address,City/State,...`. [Amex converter author's documented variants](https://github.com/jmcameron/amex2qif). Positive purchases are inverted when distinctive extended headers are present; minimal headers require `--card` |
| Generic checking/card | Signed Amount, Debit/Credit, Withdrawals/Deposits, Type or Debit/Credit direction, and Running Balance variants have hand-written test cases. `--map` resolves different names |

The script never downloads these pages or queries a bank. All runtime work is local. Plan contents, cancellation screens and pricing can change; the skill tells Claude to use the actual biller and qualify uncertain matches.
