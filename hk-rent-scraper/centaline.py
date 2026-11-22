"""Commercial rents from Centaline Commercial (oir.centanet.com).

    python centaline.py listings                       # shops to let now -> out/centaline_listings.csv
    python centaline.py transactions --start 2016-01   # leases done since then -> out/centaline_transactions.csv

`listings` are asking rents: every retail unit Centaline advertises for lease, with size,
rent, rent per square foot, the trades it suits and its position. Each run is kept under
its date in data/centaline/listings/, so repeated runs show units coming on and off the
market.

`transactions` are leases Centaline records as done, for shops, offices and industrial
units alike, one month at a time. A finished month is kept in data/centaline/transactions/
and not asked for again; the current and previous month are refreshed on every run.

Agents' names and phone numbers are not kept.

Standard library only; Python 3.9 or newer.
"""
import argparse
import csv
import gzip
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from calendar import monthrange
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "centaline"
OUT = ROOT / "out"
API = "https://oirapi.centanet.com/CentaOIRAPI_V3_Prod/api"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

LISTING_COLS = ["id", "adv_no", "property_no", "building_id", "name_en", "name_tc", "zone",
                "district", "street", "floor", "usage", "size_sqft", "rent", "rent_per_sqft",
                "rent_inclusive", "sale_price", "sale_price_per_sqft", "suited_to", "labels",
                "mtr_station", "walk", "built", "air_con", "sole_agent", "lat", "lon",
                "published", "rent_published", "collected"]
DEAL_COLS = ["id", "date", "usage", "name_en", "name_tc", "zone", "district", "floor", "unit",
             "area_sqft", "rent", "rent_per_sqft", "estimated", "source", "address",
             "building_id", "property_no"]


def get(path, **params):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)["data"]
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} for {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            pass
        time.sleep(5 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 6 tries: {url}")


def pages(fetch, size, pause):
    """Every item of a paged answer; fetch(page) returns {'totalCount', 'items'}."""
    items, page = [], 1
    while True:
        got = fetch(page)
        items += got["items"] or []
        if not got["items"] or len(items) >= got["totalCount"]:
            return items
        page += 1
        time.sleep(pause)


def save(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    tmp.rename(path)


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_csv(path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {path}")


def number(v):
    return round(v, 1) if v else ""


def listing_row(p, collected):
    area, price, where = p.get("areaInfo") or {}, p.get("priceInfo") or {}, p.get("mapInfo") or {}
    return {
        "id": p["id"], "adv_no": p.get("advNo") or "", "property_no": p.get("ibsPropertyNo") or "",
        "building_id": p.get("centabldg") or "",
        "name_en": p.get("propertyNameEn") or "", "name_tc": p.get("propertyNameCn") or "",
        "zone": area.get("zoneEn") or "", "district": area.get("districtNameEn") or "",
        "street": p.get("address") or "", "floor": p.get("floor") or "",
        "usage": p.get("propertyUsageEn") or "", "size_sqft": number(p.get("size")),
        "rent": number(price.get("rental")), "rent_per_sqft": number(price.get("avgRental")),
        "rent_inclusive": 1 if p.get("rentalInclu") else "",
        "sale_price": number(price.get("price")), "sale_price_per_sqft": number(price.get("avgPrice")),
        "suited_to": "|".join(p.get("display") or []),
        "labels": "|".join(x["value"] for x in p.get("labels") or [] if x.get("value")),
        "mtr_station": p.get("mtrStation") or "", "walk": p.get("duration") or "",
        "built": (p.get("operationData") or "")[:4],
        "air_con": "" if p.get("airCon") in (None, "--") else p["airCon"],
        "sole_agent": 1 if p.get("isSoleAgent") else "",
        "lat": where.get("lat") or "", "lon": where.get("lng") or "",
        "published": (p.get("publishDate") or "")[:10],
        "rent_published": (p.get("rentPublishDate") or "")[:10], "collected": collected,
    }


def deal_row(t):
    area, price = t.get("areaInfo") or {}, t.get("priceInfo") or {}
    blank = lambda v: "" if v in (None, "--") else v
    return {
        "id": t["id"], "date": (t.get("transactionDate") or "")[:10],
        "usage": (t.get("propertyUsageEn") or "").title(),
        "name_en": t.get("propertyNameEn") or "", "name_tc": t.get("propertyNameCn") or "",
        "zone": area.get("zoneEn") or "", "district": blank(area.get("districtNameEn")) or "",
        "floor": blank(t.get("floor")), "unit": blank(t.get("unit")),
        "area_sqft": number(t.get("transactionArea")),
        "rent": number(price.get("rental")), "rent_per_sqft": number(price.get("avgRental")),
        "estimated": 1 if t.get("isPriceEstimated") else "",
        "source": t.get("sourceDisplayName") or "",
        "address": " ".join(w for w in (t.get("addressDisplayName") or "").split() if w != "--"),
        "building_id": t.get("centabldg") or "", "property_no": t.get("ibsPropertyNo") or "",
    }


def cmd_listings(args):
    today = date.today().isoformat()
    items = pages(lambda page: get("Post/GetList", PageSize=200, usages=args.usage, pageindex=page,
                                   posttype="R", lang="EN")["postResp"], 200, args.pause)
    for p in items:
        p.pop("agentInfos", None)
    save(RAW / "listings" / f"{today.replace('-', '')}_{args.usage.lower()}.json.gz", items)
    seen = {}
    for p in items:
        seen.setdefault(p["id"], listing_row(p, today))
    write_csv(OUT / "centaline_listings.csv", LISTING_COLS, list(seen.values()))


def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)


def cmd_transactions(args):
    today = date.today()
    first = tuple(int(x) for x in args.start.split("-"))
    recent = {(today.year, today.month), (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)}
    folder = RAW / "transactions"
    for y, m in months(first, (today.year, today.month)):
        path = folder / f"{y}-{m:02}.json.gz"
        if path.exists() and (y, m) not in recent:
            continue
        span = f"01/{m:02}/{y}-{monthrange(y, m)[1]:02}/{m:02}/{y}"
        items = pages(lambda page: get("Transaction/GetTransactionList", pageindex=page, pagesize=500,
                                       daterang=span, posttype="R", lang="EN")["recordList"], 500, args.pause)
        save(path, items)
        print(f"{y}-{m:02}: {len(items)} leases", flush=True)
        time.sleep(args.pause)
    seen = {}
    for path in sorted(folder.glob("*.json.gz")):
        if path.name[:7] >= args.start:
            for t in load(path):
                seen.setdefault(t["id"], deal_row(t))
    write_csv(OUT / "centaline_transactions.csv", DEAL_COLS,
              sorted(seen.values(), key=lambda r: (r["date"], r["id"])))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("listings")
    p.add_argument("--usage", default="Retail", choices=["Retail", "Office", "Industrial"])
    p.set_defaults(fn=cmd_listings)
    p = sub.add_parser("transactions")
    p.add_argument("--start", default="2016-01", help="first month, YYYY-MM")
    p.set_defaults(fn=cmd_transactions)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
