"""Commercial rents from Centaline Commercial (oir.centanet.com).

    python centaline.py listings                       # shops to let now -> out/centaline_listings.csv
    python centaline.py transactions --start 2016-01   # leases done since then -> out/centaline_transactions.csv
    python centaline.py geocode                        # give those leases a map position
    python centaline.py rebuild                        # write both CSVs again from the saved answers

`listings` are asking rents: every retail unit Centaline advertises for lease, with size,
rent, rent per square foot, the trades it suits and its position. Each run is kept under
its date in data/centaline/listings/, so repeated runs show units coming on and off the
market.

`transactions` are leases Centaline records as done, for shops, offices and industrial
units alike, one month at a time. A finished month is kept in data/centaline/transactions/
and not asked for again; the current and previous month are refreshed on every run.

Centaline numbers every unit within the department that handles it (`dept` and
`property_no`), and a lease carries the same number as a listing of that unit. Each lease
therefore shows the lease of the same unit before it, and each listing the last lease of
the unit it advertises: when, at what rent, and under which building or street number.

`geocode` looks up each building or address named in the saved leases with the government's
Address Lookup Service and writes the transactions CSV again with `lat`, `lon` and
`placed_by`. A lookup is kept only when it agrees with the lease: `address` when the street
and street number match, `building` when the building or estate name matches, `street` when
only the street is known and the point is some building on it. Where several buildings in
Hong Kong share the name, the one nearest the lease's district is taken, and none is
accepted if even that one is more than 2 km from the district. Answers are kept in
data/centaline/places.json, so a later run only looks up new places.

`rebuild` asks for nothing: it writes the listings CSV from the newest saved run and the
transactions CSV from the saved months.

Agents' names and phone numbers are not kept.

Standard library only; Python 3.9 or newer.
"""
import argparse
import csv
import gzip
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "centaline"
OUT = ROOT / "out"
API = "https://oirapi.centanet.com/CentaOIRAPI_V3_Prod/api"
ALS = "https://www.als.gov.hk/lookup"
PLACES = RAW / "places.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

LISTING_COLS = ["id", "adv_no", "dept", "property_no", "building_id", "name_en", "name_tc", "zone",
                "district", "street", "floor", "usage", "size_sqft", "rent", "rent_per_sqft",
                "rent_inclusive", "sale_price", "sale_price_per_sqft", "suited_to", "labels",
                "mtr_station", "walk", "built", "air_con", "sole_agent", "with_key", "media", "photo",
                "lat", "lon", "published", "rent_published", "collected", "unit_leases",
                "last_lease_id", "last_let", "last_rent", "last_area_sqft", "last_name_tc"]
DEAL_COLS = ["id", "date", "usage", "name_en", "name_tc", "zone", "district", "floor", "unit",
             "area_sqft", "rent", "rent_per_sqft", "estimated", "source", "address", "dept",
             "building_id", "building_no", "property_no", "unit_leases", "previous_date",
             "previous_rent", "previous_area_sqft", "lat", "lon", "placed_by", "placed_at"]
MEDIA = {"isVideo": "video", "is360": "360", "isVR": "VR"}
STREET = re.compile(r"([\u4e00-\u9fff]+?(?:大道|道|街|路|里|坊|巷|徑|臺|台|圍|段)[東南西北中]?)\s*"
                    r"(\d+)[A-Z]?(?:\s*[-–至]\s*(\d+)[A-Z]?)?\s*號")
NUMBER_FIRST = re.compile(r"^(\d+)[A-Z]?(?:\s*[-–至]\s*(\d+)[A-Z]?)?\s*號?\s*"
                          r"([\u4e00-\u9fff]+?(?:大道|道|街|路|里|坊|巷|徑|臺|台|圍|段)[東南西北中]?)$")
STREET_ONLY = re.compile(r"(?:大道|道|街|路|里|坊|巷|徑|臺|台|圍)[東南西北中]?$")


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


def unit_leases(deals):
    """The leases of each unit, oldest first, under its department and property number."""
    units = {}
    for t in deals:
        if t.get("ibsPropertyNo"):
            units.setdefault((t["ibsDept"], t["ibsPropertyNo"]), []).append(t)
    for leases in units.values():
        leases.sort(key=lambda t: t["transactionDate"])
    return units


def listing_row(p, collected, units):
    area, price, where = p.get("areaInfo") or {}, p.get("priceInfo") or {}, p.get("mapInfo") or {}
    station = (p.get("mtrStation") or "").strip()
    leases = units.get((p["ibsDept"], p["ibsPropertyNo"])) or []
    last = leases[-1] if leases else {}
    return {
        "id": p["id"], "adv_no": p.get("advNo") or "", "dept": p.get("deptDisplayName") or "",
        "property_no": p.get("ibsPropertyNo") or "", "building_id": p.get("centabldg") or "",
        "name_en": p.get("propertyNameEn") or "", "name_tc": p.get("propertyNameCn") or "",
        "zone": area.get("zoneEn") or "", "district": area.get("districtNameEn") or "",
        "street": p.get("address") or "", "floor": p.get("floor") or "",
        "usage": p.get("propertyUsageEn") or "", "size_sqft": number(p.get("size")),
        "rent": number(price.get("rental")), "rent_per_sqft": number(price.get("avgRental")),
        "rent_inclusive": 1 if p.get("rentalInclu") else "",
        "sale_price": number(price.get("price")), "sale_price_per_sqft": number(price.get("avgPrice")),
        "suited_to": "|".join(p.get("display") or []),
        "labels": "|".join(x["value"] for x in p.get("labels") or [] if x.get("value")),
        "mtr_station": "" if station == "Station" else station, "walk": p.get("duration") or "",
        "built": (p.get("operationData") or "")[:4],
        "air_con": "" if p.get("airCon") in (None, "--") else p["airCon"],
        "sole_agent": 1 if p.get("isSoleAgent") else "", "with_key": 1 if p.get("withKey") else "",
        "media": "|".join(name for key, name in MEDIA.items() if (p.get("mediaTagInfo") or {}).get(key)),
        "photo": p.get("thumbnailPath") or "",
        "lat": where.get("lat") or "", "lon": where.get("lng") or "",
        "published": (p.get("publishDate") or "")[:10],
        "rent_published": (p.get("rentPublishDate") or "")[:10], "collected": collected,
        "unit_leases": len(leases) or "", "last_lease_id": last.get("id", ""),
        "last_let": last.get("transactionDate", "")[:10],
        "last_rent": number((last.get("priceInfo") or {}).get("rental")),
        "last_area_sqft": number(last.get("transactionArea")),
        "last_name_tc": last.get("propertyNameCn") or "",
    }


def place_key(t):
    """The building or address a lease names, with its district: what gets looked up."""
    district = (t.get("areaInfo") or {}).get("districtNameCn") or ""
    return f"{' '.join((t.get('propertyNameCn') or '').split())}|{'' if district == '--' else district}"


def deal_row(t, places, units):
    area, price = t.get("areaInfo") or {}, t.get("priceInfo") or {}
    at = places.get(place_key(t)) or {}
    leases = units.get((t["ibsDept"], t.get("ibsPropertyNo"))) or []
    earlier = [x for x in leases if x["transactionDate"] < t["transactionDate"]]
    previous = earlier[-1] if earlier else {}
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
        "dept": t.get("deptDisplayName") or "", "building_id": t.get("centabldg") or "",
        "building_no": t.get("ibsBuildingID") or "", "property_no": t.get("ibsPropertyNo") or "",
        "unit_leases": len(leases) or "", "previous_date": previous.get("transactionDate", "")[:10],
        "previous_rent": number((previous.get("priceInfo") or {}).get("rental")),
        "previous_area_sqft": number(previous.get("transactionArea")),
        "lat": at.get("lat", ""), "lon": at.get("lon", ""),
        "placed_by": at.get("by", ""), "placed_at": at.get("at", ""),
    }


def cmd_listings(args):
    today = date.today().isoformat()
    items = pages(lambda page: get("Post/GetList", PageSize=200, usages=args.usage, pageindex=page,
                                   posttype="R", lang="EN")["postResp"], 200, args.pause)
    for p in items:
        p.pop("agentInfos", None)
    save(RAW / "listings" / f"{today.replace('-', '')}_{args.usage.lower()}.json.gz", items)
    write_listings(items, today, unit_leases(saved_deals()))


def write_listings(items, collected, units):
    seen = {}
    for p in items:
        seen.setdefault(p["id"], listing_row(p, collected, units))
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
    write_deals(saved_deals())


def saved_deals():
    return [t for path in sorted((RAW / "transactions").glob("*.json.gz")) for t in load(path)]


def write_deals(deals):
    places = json.loads(PLACES.read_text()) if PLACES.exists() else {}
    units = unit_leases(deals)
    seen = {}
    for t in deals:
        seen.setdefault(t["id"], deal_row(t, places, units))
    write_csv(OUT / "centaline_transactions.csv", DEAL_COLS,
              sorted(seen.values(), key=lambda r: (r["date"], r["id"])))
    placed = sum(1 for r in seen.values() if r["lat"])
    if places:
        print(f"{placed} of {len(seen)} leases have a position")


def lookup(q):
    url = f"{ALS}?{urllib.parse.urlencode({'q': q, 'n': 10})}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "hk-rent-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("SuggestedAddress") or []
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            time.sleep(2 ** attempt + random.random())
    return None


def judge(name, suggestions):
    """Suggestions that agree with the name, each as {'lat', 'lon', 'by', 'at'}."""
    flat = name.replace(" ", "")
    asked = STREET.search(name)
    asked = asked.groups() if asked else None
    if not asked and NUMBER_FIRST.search(flat):  # '655彌敦道'
        lo, hi, street = NUMBER_FIRST.search(flat).groups()
        asked = (street, lo, hi)
    agree, street_only = [], []
    for s in suggestions:
        p = s["Address"]["PremisesAddress"]
        c, g = p.get("ChiPremisesAddress") or {}, p.get("GeospatialInformation") or {}
        if not g.get("Latitude"):
            continue
        st = c.get("ChiStreet") or {}
        building = c.get("BuildingName") or ""
        estate = (c.get("ChiEstate") or {}).get("EstateName") or ""
        at = "".join(x for x in (st.get("StreetName"), st.get("BuildingNoFrom") and st["BuildingNoFrom"] + "號",
                                 estate, building) if x)
        here = {"lat": float(g["Latitude"]), "lon": float(g["Longitude"]), "at": at}
        if asked and st.get("StreetName") and st["StreetName"] in asked[0] and st.get("BuildingNoFrom"):
            lo, hi = int(asked[1]), int(asked[2] or asked[1])
            a = int(re.match(r"\d+", st["BuildingNoFrom"]).group()) if re.match(r"\d+", st["BuildingNoFrom"]) else None
            b = int(re.match(r"\d+", st.get("BuildingNoTo") or "").group()) if re.match(r"\d+", st.get("BuildingNoTo") or "") else a
            if a is not None and a <= hi and lo <= b:
                agree.append({**here, "by": "address"})
                continue
        for known in (building, estate):
            k = known.replace(" ", "")
            if len(k) >= 3 and (k == flat or k in flat or (len(flat) >= 3 and flat in k)):
                agree.append({**here, "by": "building"})
                break
        else:
            if (not asked and STREET_ONLY.search(flat) and st.get("StreetName")
                    and flat.endswith(st["StreetName"])):
                street_only.append({**here, "by": "street"})
    return agree or street_only[:1]


def district_centres():
    """Middle of each Centaline district, from the positions of its saved listings."""
    points = {}
    for path in (RAW / "listings").glob("*.json.gz"):
        for p in load(path):
            where, name = p.get("mapInfo") or {}, (p.get("areaInfo") or {}).get("districtNameCn")
            if name and where.get("lat"):
                points.setdefault(name, []).append((where["lat"], where["lng"]))
    middle = lambda v: sorted(v)[len(v) // 2]
    return {d: (middle([a for a, _ in pts]), middle([b for _, b in pts])) for d, pts in points.items()}


CENTRES = {}


def place(key):
    name, district = key.split("|")
    if not name:
        return key, {}
    found = []
    for q in (f"{name} {district}", name) if district else (name,):
        suggestions = lookup(q)
        if suggestions is None:
            return key, None  # no answer from the service: ask again next run
        found += judge(name, suggestions)
        if found and found[0]["by"] == "address":
            break
    if not found:
        return key, {}
    best = [f for f in found if f["by"] == min(x["by"] for x in found)]  # address, building, street
    centre = CENTRES.get(district)
    if centre:
        km = lambda f: 111 * ((f["lat"] - centre[0]) ** 2 + (0.925 * (f["lon"] - centre[1])) ** 2) ** 0.5
        best.sort(key=km)
        several = len({(round(f["lat"], 3), round(f["lon"], 3)) for f in best}) > 1
        if several and best[0]["by"] == "building" and km(best[0]) > 2:
            return key, {}
    return key, best[0]


def cmd_geocode(args):
    deals = saved_deals()
    if not deals:
        raise SystemExit("no leases saved yet: run transactions first")
    places = json.loads(PLACES.read_text()) if PLACES.exists() else {}
    CENTRES.update(district_centres())
    todo = sorted({place_key(t) for t in deals} - set(places))[:args.limit]
    print(f"{len(places)} places already looked up, {len(todo)} to go", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for n, (key, found) in enumerate(ex.map(place, todo), 1):
            if found is not None:
                places[key] = found
            if n % 500 == 0 or n == len(todo):
                PLACES.write_text(json.dumps(places, ensure_ascii=False))
                print(f"  {n}/{len(todo)}", flush=True)
    how = {}
    for v in places.values():
        how[v.get("by", "not placed")] = how.get(v.get("by", "not placed"), 0) + 1
    print("places:", ", ".join(f"{n} {b}" for b, n in sorted(how.items(), key=lambda x: -x[1])))
    write_deals(deals)


def cmd_rebuild(args):
    deals = saved_deals()
    for path in sorted((RAW / "listings").glob("*.json.gz"))[-1:]:
        day = path.name[:8]
        write_listings(load(path), f"{day[:4]}-{day[4:6]}-{day[6:]}", unit_leases(deals))
    write_deals(deals)


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
    p = sub.add_parser("geocode")
    p.add_argument("--limit", type=int, help="look up at most this many places this run")
    p.set_defaults(fn=cmd_geocode)
    sub.add_parser("rebuild").set_defaults(fn=cmd_rebuild)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
