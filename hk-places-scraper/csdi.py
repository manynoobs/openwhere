"""Government lists of licensed and public premises, each with a map position.

    python csdi.py                                    # every list -> out/csdi_<name>.csv
    python csdi.py restaurant_licences pharmacies     # some of them
    python csdi.py --list

Departments publish these lists as point data on the Common Spatial Data Infrastructure
portal (portal.csdi.gov.hk). Each list is one request and comes with the position of every
premises, which the departments' own licence files do not give:

  restaurant_licences   FEHD restaurant licences
  food_licences         FEHD food licences other than restaurants
  liquor_licences       Liquor Licensing Board licensed premises
  trade_licences        FEHD places of entertainment, bathhouses, swimming pools and others
  hawker_licences       FEHD hawker licences
  public_markets        FEHD public markets
  pharmacies            Department of Health authorized sellers of poisons (pharmacies)
  medicine_sellers      Department of Health listed sellers of poisons (medicine shops)
  fitness_rooms         LCSD fitness rooms
  sports_centres        LCSD sports centres
  hotels_guesthouses    Home Affairs Department licensed hotels and guesthouses
  clubs                 Home Affairs Department clubs with a certificate of compliance
  karaoke               Home Affairs Department karaoke establishments
  cinemas               Cinemas
  ha_shopping_centres   Housing Authority shopping centres
  schools               Education Bureau registered schools
  hospitals             Hospital Authority hospitals

Each CSV keeps the department's own columns as given and adds `lat`, `lon` (WGS84) and
`collected`. Each run is kept in data/csdi/<date>_<name>.geojson.gz.

The data is (c) the Government of the Hong Kong SAR, released for free commercial and
non-commercial re-use with the source acknowledged.

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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "csdi"
OUT = ROOT / "out"
API = "https://portal.csdi.gov.hk/csdi-webpage/file-api"

# name: (dataset id, layer)
LISTS = {
    "restaurant_licences": ("fehd_rcd_1630036390312_58893", "FEHD_RL"),
    "food_licences": ("fehd_rcd_1630036111498_75446", "FEHD_FL"),
    "liquor_licences": ("fehd_rcd_1695972959083_79626", "FEHD_LL"),
    "trade_licences": ("fehd_rcd_1630036520303_61763", "FEHD_TL"),
    "hawker_licences": ("fehd_rcd_1629967776542_52851", "FEHD_HLI"),
    "public_markets": ("fehd_rcd_1629965523312_76550", "PMRK"),
    "pharmacies": ("dh_rcd_1670482195182_20237", "RP"),
    "medicine_sellers": ("dh_rcd_1670483109491_24038", "RMS"),
    "fitness_rooms": ("lcsd_rcd_1629267205215_5008", "FITNESS"),
    "sports_centres": ("lcsd_rcd_1629267205215_31341", "SC"),
    "hotels_guesthouses": ("had_rcd_1639475170528_37262", "LLHG"),
    "clubs": ("had_rcd_1639474881869_90085", "CLUB"),
    "karaoke": ("had_rcd_1639475380286_24022", "KAR"),
    "cinemas": ("cstb_rcd_1639635441187_63023", "geotagging"),
    "ha_shopping_centres": ("housingauthority_rcd_1765182630229_74012", "Commercial_Properties"),
    "schools": ("edb_rcd_1633336116013_47102", "SchoolBasicInfo"),
    "hospitals": ("fhb_rcd_1637028364270_14638", "HOSPITAL"),
}


def fetch(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hk-places-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=240) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} from {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(20 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {url}")


def collect(name, today):
    dataset, layer = LISTS[name]
    body = fetch(API + "?" + urllib.parse.urlencode(
        {"dataset_id": dataset, "format": "geojson", "layer_name": layer}))
    RAW.mkdir(parents=True, exist_ok=True)
    with gzip.open(RAW / f"{today.replace('-', '')}_{name}.geojson.gz", "wb") as f:
        f.write(body)
    features = json.loads(body)["features"]
    cols = list(dict.fromkeys(k for f in features for k in f["properties"]))
    OUT.mkdir(exist_ok=True)
    with open(OUT / f"csdi_{name}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols + ["lat", "lon", "collected"])
        for feature in features:
            lon, lat = feature["geometry"]["coordinates"][:2]
            w.writerow([feature["properties"].get(c, "") for c in cols] + [lat, lon, today])
    return len(features)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lists", nargs="*", help="lists to collect; all when none is given")
    ap.add_argument("--list", action="store_true", help="print the list names and stop")
    args = ap.parse_args()
    if args.list:
        print("\n".join(LISTS))
        return
    unknown = [n for n in args.lists if n not in LISTS]
    if unknown:
        raise SystemExit(f"unknown list: {', '.join(unknown)} (see --list)")
    today = date.today().isoformat()
    names = args.lists or list(LISTS)
    for i, name in enumerate(names):
        if i:
            time.sleep(1)
        print(f"{collect(name, today):6}  {name}", flush=True)
    print(f"{len(names)} lists -> {OUT}/csdi_<name>.csv")


if __name__ == "__main__":
    sys.exit(main())
