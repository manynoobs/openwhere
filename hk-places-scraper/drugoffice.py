"""Hong Kong shops licensed to sell medicines, from the Drug Office of the Department of Health.

    python drugoffice.py          # -> out/drugoffice.csv

Two registers kept for the Pharmacy and Poisons Board are read:

  Authorized Seller of Poisons   registered pharmacies and dispensaries, which have a pharmacist
  Listed Seller of Poisons       medicine shops and other retailers of over-the-counter
                                 medicines: drugstore and cosmetics chains, supermarkets,
                                 convenience stores

Each register is one page giving the licence number, name and address of every shop. The
Drug Office's open-data file of licensed drug dealers gives the same shops with their Chinese
name, district and telephone number but no licence number, so the two are joined on the
address. The Department of Health also publishes both registers as point data on
portal.csdi.gov.hk, which gives each shop its map position, joined on the address too. Five
requests in all; each answer is kept in data/drugoffice/.

A name written "SHOP O/B COMPANY" is split into the shop name and its operator. The registers
give addresses in English only.

Standard library only; Python 3.9 or newer.
"""
import csv
import difflib
import gzip
import html
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "drugoffice"
OUT = ROOT / "out"
SITE = "https://www.drugoffice.gov.hk/eps"
POINTS = "https://portal.csdi.gov.hk/csdi-webpage/file-api"
# register code -> licence type here, and as the open-data file words it
TYPES = {
    "4A": ("Authorized Seller of Poisons", "Retailer(Authorized Seller of Poisons)"),
    "3A": ("Listed Seller of Poisons", "Retailer(Listed Seller of Poisons)"),
}
POINT_LISTS = {"4A": ("dh_rcd_1670482195182_20237", "RP"), "3A": ("dh_rcd_1670483109491_24038", "RMS")}
ROW = re.compile(r'<td height="30"[^>]*>(\d+)</td>\s*<td[^>]*>([^<]*)</td>.*?'
                 r'<span class="busName">(.*?)</span>.*?</td>\s*<td>.*?</td><td[^>]*>(.*?)</td>', re.S)
UPDATED = re.compile(r"Last Updated:(?:&nbsp;|\s)*(\d\d)-(\d\d)-(\d{4})")
NO_CHINESE_NAME = "未有登記中文名稱"
COLS = ["licence_no", "licence_type", "name_en", "name_tc", "operator", "address_en",
        "district", "phone", "lat", "lon", "list_date", "collected"]


def fetch(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hk-places-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise SystemExit(f"HTTP {e.code} from {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(20 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {url}")


def clean(s):
    return " ".join(html.unescape(re.sub(r"<!--.*?-->|<[^>]+>", " ", s, flags=re.S)).split())


def key(address):
    return re.sub(r"[\s,]", "", address).upper()


def licences(code, page, today):
    """One row per shop on a register page, which numbers its rows from 1."""
    d, m, y = UPDATED.search(page).groups()
    found = ROW.findall(page)
    if [int(f[0]) for f in found] != list(range(1, len(found) + 1)):
        raise SystemExit(f"register {code} did not arrive whole: {len(found)} rows read")
    for _, licence_no, name, address in found:
        shop, _, operator = clean(name).partition(" O/B ")
        yield {"code": code, "licence_no": licence_no.strip(), "licence_type": TYPES[code][0],
               "name_en": shop, "operator": operator, "address_en": clean(address),
               "list_date": f"{y}-{m}-{d}", "collected": today}


def join(rows, pool, field):
    """Give each row the entry of `pool` at its address, or failing that at the closest spelling
    of it; the sources spell a few addresses differently."""
    for r in rows:
        r[field] = pool.pop((r["code"], key(r["address_en"])), None)
    for r in rows:
        if r[field] is None:
            left = [address for code, address in pool if code == r["code"]]
            near = difflib.get_close_matches(key(r["address_en"]), left, n=1, cutoff=0.8)
            r[field] = pool.pop((r["code"], near[0])) if near else None


def main():
    today = date.today().isoformat()
    sources = {"dealers.xml": f"{SITE}/psi/DrugDealerList.xml",
               **{f"{code}.html": f"{SITE}/licList?licType={code}&displayRange=all&lang=en&param="
                  for code in TYPES},
               **{f"{code}_points.geojson": f"{POINTS}?dataset_id={dataset}&format=geojson&layer_name={layer}"
                  for code, (dataset, layer) in POINT_LISTS.items()}}
    RAW.mkdir(parents=True, exist_ok=True)
    got = {}
    for n, (name, url) in enumerate(sources.items()):
        if n:
            time.sleep(1.5)
        got[name] = fetch(url)
        with gzip.open(RAW / f"{today.replace('-', '')}_{name}.gz", "wb") as f:
            f.write(got[name])

    code_of = {worded: code for code, (_, worded) in TYPES.items()}
    dealers = {}
    for d in ET.fromstring(got["dealers.xml"]):
        code = code_of.get(d.findtext("licenceType"))
        if code:
            dealers[code, key(d.findtext("companyAddress"))] = d

    points = {}
    for code in TYPES:
        for f in json.loads(got[f"{code}_points.geojson"])["features"]:
            points[code, key(f["properties"]["AddressEN"])] = f["geometry"]["coordinates"]

    rows = [r for code in TYPES for r in licences(code, got[f"{code}.html"].decode("utf-8"), today)]
    join(rows, dealers, "dealer")
    join(rows, points, "point")
    for r in rows:
        if r["point"]:
            r["lon"], r["lat"] = r["point"][:2]
        d = r["dealer"]
        if d is not None:
            name_tc = clean(d.findtext("companyName").rpartition("( ")[2].removesuffix(" )"))
            r["name_tc"] = "" if name_tc == NO_CHINESE_NAME else name_tc
            r["district"] = clean(d.findtext("district") or "")
            r["phone"] = clean(d.findtext("telNo") or "")

    OUT.mkdir(exist_ok=True)
    with open(OUT / "drugoffice.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for licence_type, n in Counter(r["licence_type"] for r in rows).most_common():
        print(f"{n:6}  {licence_type}")
    print(f"{sum(r['dealer'] is None for r in rows)} shops not found in the open-data file, "
          f"{sum(r['point'] is None for r in rows)} without a position")
    print(f"{len(rows)} shops -> {OUT / 'drugoffice.csv'}")


if __name__ == "__main__":
    sys.exit(main())
