#!/usr/bin/env python3
"""Cold proof statement Codex never sees: a FICTIONAL person's credit card export, Debit/Credit columns,
purchases positive in Debit, payments in Credit. September 2026. Writes cold-card-2026-09.csv and cold-answer-key.json."""
import csv, json, random
from decimal import Decimal as D
from pathlib import Path

random.seed(1015)
OUT = Path(__file__).resolve().parent
rows = []  # (date 'YYYY-MM-DD', description, category_truth, debit, credit)

def add(day, desc, cat, debit=None, credit=None):
    rows.append((f"2026-09-{day:02d}", desc, cat, D(debit) if debit else None, D(credit) if credit else None))

# subscriptions
add(1, "NETFLIX.COM", "Subscriptions", "17.99")
add(3, "SPOTIFY USA", "Subscriptions", "11.99")
add(4, "APPLE.COM/BILL", "Subscriptions", "10.99")      # Apple Music (overlaps Spotify)
add(6, "PEACOCK 8D3K2 PREMIUM", "Subscriptions", "10.99")
add(9, "MAX.COM", "Subscriptions", "16.99")
add(12, "PARAMOUNT+", "Subscriptions", "12.99")
add(14, "AMAZON PRIME*2K4L9", "Subscriptions", "14.99")
add(15, "CRUNCH FITNESS", "Health & Fitness", "29.99")
add(18, "NOOM INC", "Subscriptions", "209.00")          # trial converted to annual
add(20, "GOOGLE *Google One", "Subscriptions", "2.99")
add(22, "DOORDASH DASHPASS", "Subscriptions", "9.99")
# delivery
for d, m, amt in [(2,"DOORDASH*TACO BELL","18.42"),(5,"DOORDASH*PANDA EXPRESS","24.87"),(7,"UBER *EATS PENDING","31.15"),
                  (8,"DOORDASH*WINGSTOP","36.20"),(11,"GRUBHUB*FIVEGUYS","29.64"),(13,"DOORDASH*CHICK-FIL-A","21.08"),
                  (16,"UBER *EATS","27.93"),(19,"DOORDASH*SWEETGREEN","22.51"),(21,"DOORDASH*PAPA JOHNS","33.76"),
                  (24,"UBER *EATS","19.88"),(26,"DOORDASH*CHIPOTLE","25.40"),(28,"DOORDASH*SHAKE SHACK","30.12")]:
    add(d, m, "Delivery & Takeout", amt)
# double charge
add(10, "TST* BLUE DOOR COFFEE", "Restaurants & Coffee", "6.75")
add(10, "TST* BLUE DOOR COFFEE", "Restaurants & Coffee", "6.75")
# coffee habit
for d in [2,3,4,9,11,15,16,17,22,23,24,25,29,30]:
    add(d, "STARBUCKS STORE 08812", "Restaurants & Coffee", f"{random.choice(['5.45','6.25','7.15','5.95'])}")
# groceries, gas, shopping, eating out
for d, m, amt in [(1,"KROGER #0412","86.31"),(8,"TRADER JOE S #551","54.12"),(15,"KROGER #0412","92.77"),(23,"ALDI 71022","48.66"),(29,"KROGER #0412","71.04")]:
    add(d, m, "Groceries", amt)
for d, amt in [(4,"44.18"),(12,"39.70"),(19,"46.05"),(27,"41.33")]:
    add(d, "SHELL OIL 57442190", "Gas & Transit", amt)
for d, m, amt in [(6,"AMAZON MKTPL*ZX81P","38.49"),(13,"TARGET 00012345","64.20"),(17,"AMAZON MKTPL*RT55Q","22.99"),(25,"SEPHORA.COM","58.00")]:
    add(d, m, "Shopping", amt)
for d, m, amt in [(7,"SQ *THE BURGER JOINT","42.60"),(20,"OLIVE GARDEN 1192","56.85"),(27,"SQ *TAQUERIA EL SOL","24.30")]:
    add(d, m, "Restaurants & Coffee", amt)
add(14, "LYFT *RIDE SAT 11PM", "Rideshare", "23.40")
add(21, "UBER *TRIP", "Rideshare", "18.95")
add(18, "CVS/PHARMACY #04418", "Health & Fitness", "17.62")
# fees and interest
add(5, "LATE FEE", "Bank Fees & Interest", "32.00")
add(25, "INTEREST CHARGE:PURCHASES", "Bank Fees & Interest", "61.47")
add(12, "FOREIGN TRANSACTION FEE", "Bank Fees & Interest", "1.17")
add(12, "ALIEXPRESS.COM", "Shopping", "38.90")
# payment and a refund
add(8, "CAPITAL PAYMENT - THANK YOU", "Transfers", credit="150.00")
add(20, "AMAZON MKTPL*RT55Q REFUND", "Shopping", credit="22.99")

rows.sort(key=lambda r: r[0])
with open(OUT / "cold-card-2026-09.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Transaction Date", "Posted Date", "Card No.", "Description", "Category", "Debit", "Credit"])
    for date, desc, cat, deb, cre in rows:
        y, m, d = date.split("-")
        post = f"{y}-{m}-{min(int(d)+1,30):02d}"
        w.writerow([date, post, "8823", desc, "", f"{deb}" if deb else "", f"{cre}" if cre else ""])

tot_debit = sum(r[3] for r in rows if r[3])
tot_credit = sum(r[4] for r in rows if r[4])
bycat = {}
for r in rows:
    bycat[r[2]] = bycat.get(r[2], D(0)) + (r[3] or 0) - (r[4] or 0)
delivery = [r for r in rows if r[2] == "Delivery & Takeout"]
key = {
    "person": "FICTIONAL: Dana Whitfield, credit card ending 8823, September 2026",
    "lines": len(rows), "charges_total": str(tot_debit), "credits_total": str(tot_credit),
    "by_category_net": {k: str(v) for k, v in sorted(bycat.items())},
    "planted_leaks": [
        {"what": "Spotify and Apple Music (two music services)", "monthly": "10.99 or 11.99"},
        {"what": "Streaming stack: Netflix, Peacock, Max, Paramount+", "monthly": str(D('17.99')+D('10.99')+D('16.99')+D('12.99'))},
        {"what": "Noom free trial converted to an annual charge", "amount": "209.00"},
        {"what": "Double charge at Blue Door Coffee, same day", "amount": "6.75"},
        {"what": "Late fee", "amount": "32.00"},
        {"what": "Interest charge (carrying a balance)", "amount": "61.47"},
        {"what": "Foreign transaction fee", "amount": "1.17"},
        {"what": "Delivery", "count": len(delivery), "total": str(sum(r[3] for r in delivery)), "plus": "DashPass 9.99"},
        {"what": "Starbucks most weekdays", "count": sum(1 for r in rows if r[1].startswith('STARBUCKS'))},
    ],
    "traps": ["the payment is a Transfer, not income", "the Amazon refund offsets a Shopping charge",
              "purchases are positive in Debit and must come out as spending"],
}
(OUT / "cold-answer-key.json").write_text(json.dumps(key, indent=1))
print(len(rows), "lines; charges", tot_debit, "credits", tot_credit)
