"""Rents for shops in government buildings, from the Government Property Agency's tender awards.

    python gpa.py          # -> out/gpa_awards.csv

The agency lets shops, car parks and sites for vending machines and cash machines in
government buildings by tender, and publishes each award since 2021 as open data: the
premises, the tenant, the term and the monthly rent. One request reads the whole list, kept
as published in data/gpa/.

`kind` is `shop`, `car park`, `vending machine` or `ATM`, read from the description of the
premises. `food` marks a shop let to a restaurant, caterer or food retailer. The list does
not say what a shop may be used for, so this is judged from the tenant's name: a food word
in it, or one of the food operators in FOOD_TENANTS.

`rent` is HK$ a month, exclusive of rates. Where `turnover_pct` is filled, `rent` is the
minimum and the tenant pays that share of gross takings when it comes to more.

The data is from DATA.GOV.HK and may be kept and republished, crediting the Government
Property Agency.

Standard library only; Python 3.9 or newer.
"""
import csv
import io
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "gpa"
OUT = ROOT / "out"
URL = "https://www.gpa.gov.hk/doc/psi/ds/psi-cm-aclndp-cs.csv"

COLS = ["ref", "kind", "food", "premises", "premises_tc", "district", "tenant", "tenant_tc",
        "start", "years", "renewal_years", "rent", "turnover_pct", "lat", "lon"]
KINDS = {"car park": "car park", "vending machine": "vending machine", "teller machine": "ATM"}
FOOD_WORDS = re.compile(r"restaurant|catering|food|餐|飲食|食品", re.I)
# tenants whose name does not say so: 7-Eleven and Wellcome, a supermarket chain, a Japanese
# food shop, and the restaurant at 121 Peak Road
FOOD_TENANTS = ("Dairy Farm", "China Resources Vanguard", "Hyakunousha", "Modern China International")
YEARS = {"one": 1, "two": 2, "three": 3, "five": 5}
TERM = re.compile(r"(\w+) years? commencing (?:from|on) (?:the )?(\d+)(?:\w\w day of)? (\w+ \d{4})")
RENEWAL = re.compile(r"further term of (\w+) years")
RENT = re.compile(r"HK\$([\d,]+(?:\.\d+)?)")
SHARE = re.compile(r"or (\d+)% of the Gross")


def fetch():
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "hk-rent-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} from {URL}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(5 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {URL}")


def row(r):
    premises, tenant = r["en_property_address"], r["en_name_of_tenant"]
    kind = next((k for words, k in KINDS.items() if words in premises.lower()), "shop")
    years, day, month = TERM.search(r["en_tenancy_term"]).groups()
    renewal = RENEWAL.search(r["en_tenancy_term"])
    share = SHARE.search(r["en_amount"])
    food = kind == "shop" and (FOOD_WORDS.search(tenant + r["tc_name_of_tenant"])
                               or any(name in tenant for name in FOOD_TENANTS))
    return {
        "ref": r["tender_quotation_reference_number"], "kind": kind, "food": 1 if food else "",
        "premises": premises, "premises_tc": r["tc_property_address"], "district": r["en_district"],
        "tenant": tenant, "tenant_tc": r["tc_name_of_tenant"],
        "start": datetime.strptime(f"{day} {month}", "%d %B %Y").date().isoformat(),
        "years": YEARS[years.lower()],
        "renewal_years": YEARS[renewal.group(1)] if renewal else "",
        "rent": round(float(RENT.search(r["en_amount"]).group(1).replace(",", ""))),
        "turnover_pct": share.group(1) if share else "",
        "lat": float(r["latitude_lands"]), "lon": float(r["longitude_lands"]),
    }


def main():
    raw = fetch()
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / URL.rsplit("/", 1)[1]).write_bytes(raw)

    rows = sorted((row(r) for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))),
                  key=lambda r: (r["start"], r["ref"]))
    OUT.mkdir(exist_ok=True)
    with open(OUT / "gpa_awards.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    for kind, n in Counter(r["kind"] for r in rows).most_common():
        print(f"{n:6}  {kind}")
    print(f"{sum(1 for r in rows if r['food']):6}  of the shops are food businesses")
    print(f"{len(rows)} awards, {rows[0]['start']} to {rows[-1]['start']} -> {OUT / 'gpa_awards.csv'}")


if __name__ == "__main__":
    sys.exit(main())
