"""Shops and services in Hong Kong from OpenStreetMap.

    python osm.py          # -> out/osm_places.csv

One request to the Overpass API returns every mapped place of these kinds in Hong Kong:

  Restaurant                          restaurants, fast food, food courts
  Beverage shop                       cafes, coffee, tea, bubble tea and drinks shops
  Bar                                 bars and pubs
  Gym                                 fitness centres
  Pharmacy and health/beauty retail   pharmacies, chemists, cosmetics, herbalists, supplements
  Beauty and personal care            beauty salons, hairdressers, massage, spas
  Lifestyle, snack and convenience    convenience, variety, confectionery, gift, houseware
  Supermarket                         supermarkets

Each run is kept in data/osm/<date>.json.gz. `branches` counts the places in the file that
share a brand (or a name, where no brand is tagged), which is how a chain shows up.

OpenStreetMap is mapped by volunteers, so a place missing here may simply be unmapped.
The data is (c) OpenStreetMap contributors under the Open Database Licence: it may be kept
and republished with that credit. Contributors' user names are not kept.

Standard library only; Python 3.9 or newer.
"""
import csv
import gzip
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "osm"
OUT = ROOT / "out"
OVERPASS = "https://overpass-api.de/api/interpreter"
HONG_KONG = 3600913110  # Overpass area of the Hong Kong boundary relation

# OSM tag -> category; the first tag a place carries, in this order, decides
KINDS = {
    "leisure=fitness_centre": "Gym",
    "amenity=pharmacy": "Pharmacy and health/beauty retail",
    **{f"shop={v}": "Pharmacy and health/beauty retail" for v in (
        "chemist", "cosmetics", "perfumery", "herbalist", "nutrition_supplements",
        "health_food", "medical_supply")},
    **{f"shop={v}": "Beauty and personal care" for v in ("beauty", "hairdresser", "massage")},
    "amenity=spa": "Beauty and personal care", "leisure=spa": "Beauty and personal care",
    **{f"shop={v}": "Lifestyle, snack and convenience" for v in (
        "convenience", "variety_store", "confectionery", "gift", "houseware")},
    "shop=supermarket": "Supermarket",
    "amenity=cafe": "Beverage shop",
    **{f"shop={v}": "Beverage shop" for v in ("beverages", "coffee", "tea", "bubble_tea")},
    **{f"amenity={v}": "Restaurant" for v in ("restaurant", "fast_food", "food_court")},
    "amenity=bar": "Bar", "amenity=pub": "Bar",
}
COLS = ["osm_id", "category", "kind", "name", "name_en", "name_zh", "brand", "branches",
        "house_number", "street", "building", "unit", "level", "lat", "lon", "phone",
        "website", "opening_hours", "cuisine", "openrice_id", "edited", "collected"]


def query():
    by_key = {}
    for kind in KINDS:
        k, v = kind.split("=")
        by_key.setdefault(k, []).append(v)
    wanted = "\n".join(f'  nwr(area.hk)["{k}"~"^({"|".join(vs)})$"];' for k, vs in by_key.items())
    return f"[out:json][timeout:180];\narea({HONG_KONG})->.hk;\n(\n{wanted}\n);\nout center meta;"


def fetch():
    body = urllib.parse.urlencode({"data": query()}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(OVERPASS, data=body, headers={"User-Agent": "hk-places-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.load(r)["elements"]
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} from {OVERPASS}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            pass
        time.sleep(20 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {OVERPASS}")


def kind_of(tags):
    return next((k for k in KINDS if tags.get(k.split("=")[0]) == k.split("=")[1]), None)


def row(e, today):
    t = e["tags"]
    where = e if "lat" in e else e.get("center", {})
    kind = kind_of(t)
    return {
        "osm_id": f"{e['type']}/{e['id']}", "category": KINDS[kind], "kind": kind,
        "name": t.get("name", ""), "name_en": t.get("name:en", ""),
        "name_zh": t.get("name:zh") or t.get("name:zh-Hant", ""),
        "brand": t.get("brand", ""),
        "house_number": t.get("addr:housenumber", ""), "street": t.get("addr:street", ""),
        "building": t.get("addr:housename", ""), "unit": t.get("addr:unit", ""),
        "level": t.get("level:ref") or t.get("level", ""),
        "lat": where.get("lat", ""), "lon": where.get("lon", ""),
        "phone": t.get("phone") or t.get("contact:phone", ""),
        "website": t.get("website") or t.get("contact:website", ""),
        "opening_hours": t.get("opening_hours", ""), "cuisine": t.get("cuisine", ""),
        "openrice_id": t.get("ref:openrice", ""),
        "edited": (e.get("timestamp") or "")[:10], "collected": today,
    }


def main():
    today = date.today().isoformat()
    elements = fetch()
    for e in elements:
        for k in ("user", "uid", "changeset"):
            e.pop(k, None)
    RAW.mkdir(parents=True, exist_ok=True)
    with gzip.open(RAW / f"{today.replace('-', '')}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False)

    rows = [row(e, today) for e in elements if kind_of(e["tags"])]
    chain = Counter(r["brand"] or r["name"] for r in rows if r["brand"] or r["name"])
    for r in rows:
        r["branches"] = chain.get(r["brand"] or r["name"], "")
    rows.sort(key=lambda r: (r["category"], r["brand"] or r["name"], r["osm_id"]))
    OUT.mkdir(exist_ok=True)
    with open(OUT / "osm_places.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    for category, n in Counter(r["category"] for r in rows).most_common():
        print(f"{n:6}  {category}")
    print(f"{len(rows)} places -> {OUT / 'osm_places.csv'}")


if __name__ == "__main__":
    sys.exit(main())
