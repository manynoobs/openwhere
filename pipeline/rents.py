"""Shop rents around each unit, from Centaline Commercial leases and listings.

    python pipeline/rents.py     # after export.py; adds `rent` to web/public/data/units/<id>.json
                                 # and `rent` to meta.json

Reads the CSVs that hk-rent-scraper writes (centaline_transactions.csv, centaline_listings.csv,
rvd_retail_rents.csv) from hk-rent-scraper/out/. Only medians reach the app, never a single lease.

For each unit:
  - leases: recorded (not estimated) retail leases of the last three years on the same level
    (street-level shops for a street-level unit, upstairs shops otherwise), within 150 m, or
    within 300 m when 150 m holds fewer than 5. Leases placed only by street are left out.
  - asking: units advertised for lease now on the same level within 300 m.
"""
import csv
import json
import math
import statistics
from datetime import date

from ingest import ROOT

SRC = ROOT / "hk-rent-scraper" / "out"
OUT = ROOT / "web" / "public" / "data"
RADII = (150, 300)
MIN_LEASES = 5
YEARS_BACK = 3
STREET = {"Shop", "Ground Shop"}
UPSTAIRS = {"Upstairs Shop", "1/F"}
STREET_LISTING = {"Shop", "Ground Floor"}
UPSTAIRS_LISTING = {"Low Floor", "Middle Floor", "High Floor"}


def dist_m(a, b):
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return 6371000 * math.hypot(math.radians(b[0] - a[0]) * k, math.radians(b[1] - a[1]))


def num(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def read(name):
    return list(csv.DictReader(open(SRC / name, encoding="utf-8-sig")))


def near(rows, at, radius):
    return [r for r in rows if dist_m(at, r["at"]) <= radius]


def summary(rows):
    psf = sorted(r["psf"] for r in rows)
    q = statistics.quantiles(psf, n=4) if len(psf) >= 4 else [psf[0], statistics.median(psf), psf[-1]]
    return {
        "n": len(rows),
        "psf": round(statistics.median(psf)),
        "psf_low": round(q[0]),
        "psf_high": round(q[2]),
        "area": round(statistics.median(r["area"] for r in rows)),
        "rent": round(statistics.median(r["rent"] for r in rows), -2),
    }


def main():
    today = date.today()
    since = date(today.year - YEARS_BACK, today.month, 1).isoformat()

    leases = {"street": [], "upstairs": []}
    for t in read("centaline_transactions.csv"):
        if t["estimated"] or t["placed_by"] not in ("address", "building") or t["date"] < since:
            continue
        level = "street" if t["floor"] in STREET else "upstairs" if t["floor"] in UPSTAIRS else None
        psf, area, rent = num(t["rent_per_sqft"]), num(t["area_sqft"]), num(t["rent"])
        if level and psf and area and rent and t["lat"]:
            leases[level].append({"at": (float(t["lon"]), float(t["lat"])), "psf": psf, "area": area, "rent": rent})

    asking = {"street": [], "upstairs": []}
    listings = read("centaline_listings.csv")
    for t in listings:
        level = "street" if t["floor"] in STREET_LISTING else "upstairs" if t["floor"] in UPSTAIRS_LISTING else None
        psf, area, rent = num(t["rent_per_sqft"]), num(t["size_sqft"]), num(t["rent"])
        if level and psf and area and rent and t["lat"]:
            asking[level].append({"at": (float(t["lon"]), float(t["lat"])), "psf": psf, "area": area, "rent": rent})

    gj = json.load(open(OUT / "units.geojson"))
    with_leases = 0
    for f in gj["features"]:
        p = f["properties"]
        at = tuple(f["geometry"]["coordinates"])
        level = "street" if p["sl"] else "upstairs"
        rent = {"level": level, "since": since, "leases": None, "asking": None}
        for radius in RADII:
            got = near(leases[level], at, radius)
            if len(got) >= MIN_LEASES:
                rent["leases"] = {**summary(got), "radius": radius}
                break
        got = near(asking[level], at, RADII[-1])
        if got:
            rent["asking"] = {**summary(got), "radius": RADII[-1]}
        with_leases += rent["leases"] is not None

        path = OUT / "units" / f"{p['id']}.json"
        detail = json.load(open(path))
        detail["rent"] = rent
        json.dump(detail, open(path, "w"), ensure_ascii=False, separators=(",", ":"))

    rvd = [r for r in read("rvd_retail_rents.csv") if r["frequency"] == "quarter" and r["area"] == "Kowloon"]
    last = max(rvd, key=lambda r: r["period"])
    meta_path = OUT / "meta.json"
    meta = json.load(open(meta_path))
    meta["rent"] = {
        "kowloon_psf": round(float(last["rent_per_sqft"]), 1),
        "kowloon_period": last["period"],
        "kowloon_provisional": last["rent_note"] == "P",
        "since": since,
        "listings_collected": max(t["collected"] for t in listings),
        "units_with_leases": with_leases,
    }
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"rents: {with_leases} of {len(gj['features'])} units have nearby leases; "
          f"{len(leases['street'])} street and {len(leases['upstairs'])} upstairs leases since {since}")


if __name__ == "__main__":
    main()
