"""Shop rents, prices and rateable values from the Rating and Valuation Department.

    python rvd.py          # -> out/rvd_retail_rents.csv, out/rvd_retail_indices.csv,
                           #    out/rvd_yields.csv, out/rvd_shop_rateable_values.csv

The department's Property Market Statistics give, for private retail premises:

  rvd_retail_rents.csv     average rent and price by area (Hong Kong Island, Kowloon, New
                           Territories; New Kowloon as well until 1998), by year and quarter
                           from 1989 and by month from 1999
  rvd_retail_indices.csv   rental and price indices for the whole territory, 1999 = 100, by
                           year and quarter from 1978 and by month from 1993
  rvd_yields.csv           market yields for retail, offices and flatted factories, by year
                           from 1987, by quarter from 1990 and by month from 1999

Rents are HK$ per square metre of internal floor area a month and prices HK$ per square
metre, as published; the per square foot columns are the same figures divided by 10.764.
An average moves with the mix of premises let in the period, so change over time is read
from the indices. Notes are the department's: `P` provisional, `Z` fewer than 20
transactions, `@` and `~` an office yield that leaves out some months.

rvd_shop_rateable_values.csv is the one table below those three areas: the number of shops
in the Valuation List and their total rateable value in each of the 18 districts, as at
1 April of each year from 2021. Rateable value is the department's estimate of a year's
rent at the 1 October before, so `shop_mean_rateable_value` is the estimated yearly rent of
the average shop in the district. Earlier years are read from the DATA.GOV.HK archive of
the file.

Files are kept as published in data/rvd/. The data is from DATA.GOV.HK and may be kept and
republished, crediting the Rating and Valuation Department.

Standard library only; Python 3.9 or newer.
"""
import csv
import io
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "rvd"
OUT = ROOT / "out"
FILES = "https://www.rvd.gov.hk/datagovhk/"
ARCHIVE = "https://api.data.gov.hk/v1/historical-archive"
VALUATION_LIST = "http://www.rvd.gov.hk/datagovhk/summary_statistics_table_8.csv"  # as the archive names it

RENTS = ["3.1A(89-98).csv", "3.1A(from_99).csv", "3.1Q(89-98).csv", "3.1Q(from_99).csv", "3.1M.csv"]
INDICES = ["3.2A.csv", "3.2Q.csv", "3.2M.csv"]
YIELDS = ["5.2A.csv", "5.2Q.csv", "5.2M.csv"]
AREAS = ["Hong Kong", "Kowloon", "New Kowloon", "New Territories"]
FREQUENCIES = ["year", "quarter", "month"]
USES = {"Retail": "retail", "Offices - Grade A": "office_a", "Offices - Grade B": "office_b",
        "Flatted Factories": "flatted_factory"}
SQFT = 10.764  # square feet in a square metre

RENT_COLS = ["frequency", "period", "area", "rent_per_sqm", "rent_per_sqft", "rent_note",
             "price_per_sqm", "price_per_sqft", "price_note"]
INDEX_COLS = ["frequency", "period", "rent_index", "rent_note", "price_index", "price_note"]
YIELD_COLS = ["frequency", "period"] + [f"{use}_{c}" for use in USES.values() for c in ("yield", "note")]
VALUE_COLS = ["as_at", "area", "district", "shops", "shop_rateable_value_000", "shop_mean_rateable_value",
              "other_commercial", "other_commercial_rateable_value_000"]


def get(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hk-rent-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            time.sleep(1)
            return raw
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} from {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(5 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {url}")


def save(name, raw):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / name).write_bytes(raw)
    return raw.decode("utf-8-sig")


def series(names):
    """Rows of the named statistics files, each with `frequency` and `period`."""
    for name in names:
        text = save(name, get(FILES + name))
        for r in csv.DictReader(io.StringIO(text.split("\n", 1)[1], newline="")):  # line 1 is a title
            frequency, when = next(iter(r.items()))
            when = when.strip()
            if frequency == "Month":      # 01-1999
                when = f"{when[3:]}-{when[:2]}"
            elif frequency == "Quarter":  # 01-03/1999
                when = f"{when[6:]}-Q{int(when[3:5]) // 3}"
            yield {**r, "frequency": frequency.lower(), "period": when}


def number(v):
    v = v.strip()
    return "" if v in ("-", "^") else v  # no transactions, too few to analyse


def rents():
    for r in series(RENTS):
        for area in AREAS:
            if f"Rents ({area})" in r:
                rent, price = number(r[f"Rents ({area})"]), number(r[f"Prices ({area})"])
                yield {"frequency": r["frequency"], "period": r["period"], "area": area,
                       "rent_per_sqm": rent, "rent_per_sqft": round(float(rent) / SQFT, 1),
                       "rent_note": r[f"Rents ({area}) - Remarks"],
                       "price_per_sqm": price, "price_per_sqft": round(float(price) / SQFT),
                       "price_note": r[f"Prices ({area}) - Remarks"]}


def indices():
    for r in series(INDICES):
        yield {"frequency": r["frequency"], "period": r["period"],
               "rent_index": number(r["Rents"]), "rent_note": r["Rents - Remarks"],
               "price_index": number(r["Prices"]), "price_note": r["Prices - Remarks"]}


def yields():
    for r in series(YIELDS):
        row = {"frequency": r["frequency"], "period": r["period"]}
        for theirs, use in USES.items():
            row[f"{use}_yield"], row[f"{use}_note"] = number(r[theirs]), r[f"{theirs} - Remarks"]
        yield row


def rateable_values():
    span = {"url": VALUATION_LIST, "start": "20150101",
            "end": (date.today() - timedelta(days=1)).strftime("%Y%m%d")}
    versions = json.loads(get(f"{ARCHIVE}/list-file-versions?{urllib.parse.urlencode(span)}"))["timestamps"]
    # the list is posted in draft each March and in final form each April: the year's last is final
    for stamp in {v[:4]: v for v in sorted(versions)}.values():
        at = {"url": VALUATION_LIST, "time": stamp}
        text = save(f"summary_statistics_table_8_{stamp[:8]}.csv",
                    get(f"{ARCHIVE}/get-file?{urllib.parse.urlencode(at)}"))
        title, table = text.split("\n", 1)
        as_at = datetime.strptime(re.search(r"as at (\d+ \w+ \d{4})", title).group(1), "%d %B %Y").date()
        districts = []
        for r in csv.reader(io.StringIO(table, newline="")):
            if r[0] == "District":
                continue
            shops, shop_value, other, other_value = (int(v.replace(",", "")) for v in r[1:])
            row = {"as_at": as_at.isoformat(), "shops": shops, "shop_rateable_value_000": shop_value,
                   "shop_mean_rateable_value": round(shop_value * 1000 / shops),
                   "other_commercial": other, "other_commercial_rateable_value_000": other_value}
            if r[0] in AREAS or r[0] == "OVERALL":  # a total, after the districts it sums
                area = r[0].title()
                yield from ({**d, "area": area} for d in districts)
                yield {**row, "area": area}
                districts = []
            else:
                districts.append({**row, "district": r[0]})


def by_period(rows):
    return sorted(rows, key=lambda r: (FREQUENCIES.index(r["frequency"]), r["period"]))


def write(name, cols, rows, when):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    years = sorted(r[when][:4] for r in rows)
    print(f"{len(rows):6} rows, {years[0]} to {years[-1]} -> {OUT / name}")


def main():
    write("rvd_retail_rents.csv", RENT_COLS, by_period(rents()), "period")
    write("rvd_retail_indices.csv", INDEX_COLS, by_period(indices()), "period")
    write("rvd_yields.csv", YIELD_COLS, by_period(yields()), "period")
    write("rvd_shop_rateable_values.csv", VALUE_COLS, list(rateable_values()), "as_at")


if __name__ == "__main__":
    sys.exit(main())
