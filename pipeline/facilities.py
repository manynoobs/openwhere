"""Places that draw people, and MTR exits, across Hong Kong, from the government's iGeoCom
points of interest, and pharmacies and medicine shops from the Drug Office register.

    python pipeline/facilities.py     # writes web/public/data/facilities.geojson
                                      # and adds `mtr` (metres to the nearest MTR exit) to units

Reads hk-places-scraper/out/igeocom_places.csv and hk-places-scraper/out/drugoffice.csv.
Distances are straight-line, not walking routes, and the app says so.
"""
import csv
import json
import math
import re

from ingest import ROOT

PLACES = ROOT / "hk-places-scraper" / "out"
OUT = ROOT / "web" / "public" / "data"

KINDS = {
    "mtr": "MTR exit",
    "transit": "Station or terminus",
    "hotel": "Hotel",
    "school": "School or university",
    "mall": "Mall or market",
    "landmark": "Landmark or venue",
    "hospital": "Hospital",
    "pharmacy": "Pharmacy or medicine shop",
}

# iGeoCom facility types -> the app's place kinds
IGEOCOM = {
    "Railway Station Entrance": "mtr",
    "Railway Station": "transit",
    "High Speed Rail Station": "transit",
    "Light Rail Station": "transit",
    "Bus Terminus": "transit",
    "Ferry Pier": "transit",
    "Hotel": "hotel",
    "Primary School": "school",
    "Secondary School": "school",
    "Post-Secondary": "school",
    "Mall / Shopping Centre / Commercial Complex": "mall",
    "Market": "mall",
    "Exhibition Venue": "landmark",
    "Cinema": "landmark",
    "Performing Arts Venue": "landmark",
    "Stadium": "landmark",
    "Hospital": "hospital",
}
# "MTR Admiralty Station-A Exit", "Mass Transit Railway Yau Ma Tei Station Access"
EXIT = re.compile(r"^(?:MTR|Mass Transit Railway)\s+(?P<st>.+?)\s+Station(?:\s*-\s*(?P<ref>\S+))?\s+(?:Exit|Access)$")


def dist_m(a, b):
    """Equirectangular distance in metres; plenty for a few kilometres."""
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return 6371000 * math.hypot(math.radians(b[0] - a[0]) * k, math.radians(b[1] - a[1]))


def point(lon, lat, props):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": props}


def main():
    feats, seen = [], set()
    for r in csv.DictReader(open(PLACES / "igeocom_places.csv", encoding="utf-8-sig")):
        kind = IGEOCOM.get(r["type_name"])
        if not kind or not r["lat"]:
            continue
        lon, lat = float(r["lon"]), float(r["lat"])
        props = {"k": kind, "en": r["name_en"], "tc": r["name_zh"]}
        if kind == "mtr":
            m = EXIT.match(r["name_en"])
            if not m:
                continue
            props = {"k": kind, "en": f"Exit {m['ref']}" if m["ref"] else "Exit", "tc": "", "st": m["st"]}
        elif not (props["en"] or props["tc"]):
            continue
        key = (kind, props["en"] or props["tc"], props.get("st"), round(lon, 4), round(lat, 4))
        if key in seen:
            continue
        seen.add(key)
        feats.append(point(lon, lat, props))

    for r in csv.DictReader(open(PLACES / "drugoffice.csv", encoding="utf-8-sig")):
        if r["lat"]:
            feats.append(point(float(r["lon"]), float(r["lat"]),
                               {"k": "pharmacy", "en": r["name_en"].title(), "tc": r["name_tc"]}))

    json.dump({"type": "FeatureCollection", "features": feats}, open(OUT / "facilities.geojson", "w"),
              ensure_ascii=False, separators=(",", ":"))
    counts = {}
    for f in feats:
        counts[f["properties"]["k"]] = counts.get(f["properties"]["k"], 0) + 1
    print("facilities:", counts)

    # metres from each unit to the nearest MTR exit
    exits = [(f["geometry"]["coordinates"], f["properties"]) for f in feats if f["properties"]["k"] == "mtr"]
    gj_path = OUT / "units.geojson"
    gj = json.load(open(gj_path))
    for f in gj["features"]:
        c = f["geometry"]["coordinates"]
        d, props = min(((dist_m(c, e), p) for e, p in exits), key=lambda x: x[0])
        f["properties"]["mtr"] = int(round(d))
        f["properties"]["mtrx"] = f"{props['st']} {props['en']}"
    json.dump(gj, open(gj_path, "w"), ensure_ascii=False, separators=(",", ":"))
    ds = sorted(f["properties"]["mtr"] for f in gj["features"])
    print(f"MTR exit distance: median {ds[len(ds) // 2]} m, max {ds[-1]} m")


if __name__ == "__main__":
    main()
