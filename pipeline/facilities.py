"""Places that draw people, and MTR exits, around the district, from OpenStreetMap,
and pharmacies and medicine shops from the Drug Office register.

    python pipeline/facilities.py     # writes web/public/data/facilities.geojson
                                      # and adds `mtr` (metres to the nearest MTR exit) to units

OpenStreetMap is fetched once from the Overpass API and cached in data/osm_facilities.json.
The register is read from hk-places-scraper/out/drugoffice.csv when it is there. Distances are
straight-line, not walking routes, and the app says so.
"""
import csv
import json
import math
import re
import urllib.parse
import urllib.request

from ingest import ROOT

CACHE = ROOT / "data" / "osm_facilities.json"
DRUG_OFFICE = ROOT / "hk-places-scraper" / "out" / "drugoffice.csv"
OUT = ROOT / "web" / "public" / "data"
BBOX = (22.282, 114.148, 22.330, 114.200)  # south, west, north, east: Yau Tsim and a margin
KOWLOON_SOUTH = 22.2915  # drop Hong Kong Island features that fall inside the box
REAL_SCHOOL = re.compile(r"school|college|universit|kindergarten|學校|書院|中學|小學|幼稚園|大學|學院|polytechnic", re.I)
NOT_SCHOOL = re.compile(r"abacus|tutor|learning|classes|education cent|補習|教育中心|academy of|study", re.I)

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

QUERY = """
[out:json][timeout:60];
(
  node["railway"="subway_entrance"]({b});
  nwr["railway"="station"]["station"="subway"]({b});
  nwr["public_transport"="station"]({b});
  nwr["amenity"~"^(bus_station|ferry_terminal)$"]({b});
  nwr["tourism"="hotel"]({b});
  nwr["amenity"~"^(school|university|college)$"]({b});
  nwr["shop"~"^(mall|department_store)$"]({b});
  nwr["amenity"="marketplace"]({b});
  nwr["tourism"~"^(attraction|museum|gallery)$"]({b});
  nwr["amenity"~"^(theatre|cinema|arts_centre|exhibition_centre)$"]({b});
  nwr["leisure"="stadium"]({b});
  nwr["amenity"="hospital"]({b});
);
out center tags;
"""


def fetch():
    if CACHE.exists():
        return json.load(open(CACHE))
    b = ",".join(str(v) for v in BBOX)
    data = urllib.parse.urlencode({"data": QUERY.replace("{b}", b)}).encode()
    req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=data,
                                 headers={"User-Agent": "openwhere/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.load(r)
    json.dump(body, open(CACHE, "w"), ensure_ascii=False)
    return body


def is_mtr_station(t):
    # tagged inconsistently: some carry railway=station, some only station=subway/train
    return t.get("station") in ("subway", "train") or (t.get("railway") == "station" and "MTR" in t.get("operator", ""))


def kind_of(t):
    if t.get("railway") == "subway_entrance":
        return "mtr"
    if t.get("railway") == "station" or t.get("public_transport") == "station" or \
            t.get("amenity") in ("bus_station", "ferry_terminal"):
        return "transit"
    if t.get("tourism") == "hotel":
        return "hotel"
    if t.get("amenity") in ("school", "university", "college"):
        return "school"
    if t.get("shop") in ("mall", "department_store") or t.get("amenity") == "marketplace":
        return "mall"
    if t.get("amenity") == "hospital":
        return "hospital"
    return "landmark"


def dist_m(a, b):
    """Equirectangular distance in metres; plenty for a few kilometres."""
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return 6371000 * math.hypot(math.radians(b[0] - a[0]) * k, math.radians(b[1] - a[1]))


def main():
    body = fetch()
    feats, seen = [], set()
    for e in body["elements"]:
        t = e.get("tags", {})
        lon, lat = (e["lon"], e["lat"]) if "lon" in e else (e["center"]["lon"], e["center"]["lat"])
        if lat < KOWLOON_SOUTH:
            continue
        kind = kind_of(t)
        name_all = " ".join(filter(None, [t.get("name"), t.get("name:en"), t.get("name:zh")]))
        if kind == "school" and t.get("amenity") == "school" and (not REAL_SCHOOL.search(name_all) or NOT_SCHOOL.search(name_all)):
            continue
        name_en = t.get("name:en") or (t.get("name") if t.get("name", "").isascii() else None)
        name_zh = t.get("name:zh") or t.get("name:zh-Hant") or (None if t.get("name", "").isascii() else t.get("name"))
        if kind == "mtr":
            ref = t.get("ref") or t.get("name") or ""
            name_en, name_zh = f"Exit {ref}".strip(), None
        if kind != "mtr" and not (name_en or name_zh):
            continue  # an unnamed school building or hotel annex says nothing on a map
        key = (kind, name_en or name_zh, round(lon, 3), round(lat, 3))
        if key in seen:
            continue
        seen.add(key)
        props = {"k": kind, "en": name_en or "", "tc": name_zh or ""}
        if is_mtr_station(t):
            props["mtrst"] = 1
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                      "properties": props})

    if DRUG_OFFICE.exists():
        for r in csv.DictReader(open(DRUG_OFFICE, encoding="utf-8-sig")):
            if not r["lat"]:
                continue
            lat, lon = float(r["lat"]), float(r["lon"])
            if not (KOWLOON_SOUTH <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]):
                continue
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                          "properties": {"k": "pharmacy", "en": r["name_en"].title(), "tc": r["name_tc"]}})

    # name each MTR exit after its nearest station
    stations = [f for f in feats if f["properties"].get("mtrst")]
    for f in feats:
        p = f["properties"]
        if p["k"] == "mtr" and stations:
            s = min(stations, key=lambda s: dist_m(s["geometry"]["coordinates"], f["geometry"]["coordinates"]))
            st = s["properties"]
            p["st"] = re.sub(r"\s*(MTR|Station)\b", "", st["en"] or st["tc"]).strip()

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
        f["properties"]["mtrx"] = f"{props.get('st', '')} {props['en']}".strip()
    json.dump(gj, open(gj_path, "w"), ensure_ascii=False, separators=(",", ":"))
    ds = sorted(f["properties"]["mtr"] for f in gj["features"])
    print(f"MTR exit distance: median {ds[len(ds) // 2]} m, max {ds[-1]} m")


if __name__ == "__main__":
    main()
