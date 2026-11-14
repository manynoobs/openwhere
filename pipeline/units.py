"""Resolve licence addresses to physical units.

    python pipeline/units.py parse            # parse every distinct address in spans
    python pipeline/units.py geocode [--dist 61,62] [--workers 3]
    python pipeline/units.py build            # unit keys, positions -> table units, unit_addresses

Parsing is by rule on the English address: floors, shop numbers, street number and street
name. The building comes from the Address Lookup Service (ALS), cached in
data/geocode_cache.sqlite, and is accepted only when ALS returns the same street name and a
street number that matches the one parsed from the licence. The unit key is building +
floor set + shop set. Addresses marked "portion", or with no shop number in a building
where other licences give one on that floor, are kept at building level only.
"""
import argparse
import json
import math
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import duckdb

from ingest import DB, ROOT

CACHE = ROOT / "data" / "geocode_cache.sqlite"

STREET_WORDS = (r"STREET|ROAD|AVENUE|LANE|TERRACE|PATH|DRIVE|SQUARE|CIRCUIT|CRESCENT|"
                r"BOULEVARD|HIGHWAY|PLACE|COURT|WAY|BAZAAR|RISE|HILL|PARADE|PROMENADE|"
                r"PRAYA|GARDENS?|VILLAGE|ST|RD|AVE|WALK|ESPLANADE")
ABBREV = {"ST": "STREET", "RD": "ROAD", "AVE": "AVENUE"}
NUM = r"\d+[A-Z]?(?:\s*-\s*\d*[A-Z]?)?"
STREET_RE = re.compile(
    rf"(?:NOS?\.?\s*)?(?P<num>{NUM}(?:\s*(?:,|&|AND)\s*{NUM})*),?\s+"
    rf"(?P<name>(?:[A-Z']+\s+){{0,4}}?(?:{STREET_WORDS}))\b(?:\s+(?P<dir>EAST|WEST|NORTH|SOUTH))?")
FLOOR_RE = re.compile(
    r"\b(?:(?P<g>G/F|GROUND\s+FLOOR|G\s*/\s*F|LEVEL\s+0|UG/F|UPPER\s+GROUND\s+FLOOR)"
    r"|(?P<lg>LG/F|LOWER\s+GROUND\s+FLOOR|B\d?/F|BASEMENT)"
    r"|(?P<n>\d{1,3})\s*/\s*F|(?:LEVEL|L)\s*(?P<lv>\d{1,3}[A-Z]?)\b|(?P<word>FIRST|SECOND|THIRD)\s+FLOOR"
    r"|(?P<m>M/F|MEZZANINE\s+FLOOR|CK/F|CAFE\s+FLOOR|ROOF|R/F))")
SHOP_RE = re.compile(
    r"\b(?:SHOPS?|UNITS?|STALLS?|KIOSKS?|FLAT|RM|ROOM|CUBICLE)\s*(?:NOS?\.?\s*)?"
    r"(?P<ids>[A-Z]?\d*[A-Z]?\d*(?:\s*(?:-|,|&|AND|TO)\s*[A-Z]?\d+[A-Z]?(?![\d/])(?!\s*/)"
    r"|\s*(?:-|,|&|AND)\s*[A-Z]\b(?!\s*/))*)")
WORD_FLOORS = {"FIRST": "1", "SECOND": "2", "THIRD": "3"}


def norm_street(name, direction=None):
    words = name.split()
    words[-1] = ABBREV.get(words[-1], words[-1])
    s = " ".join(words)
    return f"{s} {direction}" if direction else s


def expand_ids(text):
    """'1-3 & 5A' -> {'1','2','3','5A'}; letter ranges 'A-C' -> {'A','B','C'}."""
    out = set()
    for part in re.split(r"\s*(?:,|&|AND)\s*", text.strip()):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"([A-Z]?)(\d+)\s*(?:-|TO)\s*\1?(\d+)", part)
        if m and int(m.group(3)) - int(m.group(2)) < 30:
            out |= {f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)}
            continue
        m = re.fullmatch(r"([A-Z])\s*-\s*([A-Z])", part)
        if m:
            out |= {chr(c) for c in range(ord(m.group(1)), ord(m.group(2)) + 1)}
            continue
        out.add(re.sub(r"\s+", "", part))
    return out


def parse(address):
    a = address.upper().replace("．", ".")
    a = re.sub(r"\s+", " ", a)
    rec = {"floors": [], "shops": [], "street_no": None, "street": None, "portion": "PORTION" in a}
    floors = set()
    for m in FLOOR_RE.finditer(a):
        if m.group("g"):
            floors.add("G")
        elif m.group("lg"):
            floors.add("LG")
        elif m.group("n"):
            floors.add(m.group("n").lstrip("0") or "G")
        elif m.group("lv"):
            floors.add(m.group("lv").lstrip("0") or "G")
        elif m.group("word"):
            floors.add(WORD_FLOORS[m.group("word")])
        elif m.group("m"):
            floors.add("M")
    rec["floors"] = sorted(floors)
    shops = set()
    for m in SHOP_RE.finditer(a):
        if m.group("ids"):
            shops |= expand_ids(m.group("ids"))
    rec["shops"] = sorted(s for s in shops if s)
    m = None
    for m in STREET_RE.finditer(a):
        # skip floor-like hits such as "1/F" being read as a number
        if not re.fullmatch(r"(?:[A-Z']+\s+){0,4}?(?:%s)" % STREET_WORDS, m.group("name")):
            continue
        break
    if m:
        first = re.split(r"\s*(?:,|&|AND)\s*", m.group("num"))[0]
        rec["street_no"] = re.sub(r"\s+", "", first)
        rec["street"] = norm_street(m.group("name"), m.group("dir"))
    return rec


def street_level(floors):
    return "G" in floors


# ---------------------------------------------------------------- geocoding

def cache():
    con = sqlite3.connect(CACHE, check_same_thread=False, timeout=60)
    con.execute("CREATE TABLE IF NOT EXISTS als (q TEXT PRIMARY KEY, body TEXT, t REAL)")
    return con


def als(q):
    url = "https://www.als.gov.hk/lookup?" + urllib.parse.urlencode({"q": q, "n": 5})
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "openwhere/0.1"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode()
        except Exception:
            time.sleep(2 ** attempt)
    return None


def first_no(s):
    m = re.match(r"\d+", s or "")
    return int(m.group()) if m else None


def accept(body, street, street_no):
    """Pick the ALS suggestion whose street name and number agree with the parse."""
    try:
        sugg = json.loads(body).get("SuggestedAddress", [])
    except (TypeError, json.JSONDecodeError):
        return None
    want = first_no(street_no)
    for s in sugg:
        p = s["Address"]["PremisesAddress"]
        st = p.get("EngPremisesAddress", {}).get("EngStreet", {})
        if not st or st.get("StreetName") != street:
            continue
        lo, hi = first_no(st.get("BuildingNoFrom")), first_no(st.get("BuildingNoTo"))
        if lo is None or want is None:
            continue
        if want == lo or (hi and lo <= want <= hi) or (
                st.get("BuildingNoFrom", "").upper() == street_no.split("-")[0]):
            g = p["GeospatialInformation"]
            return {"geo": p["GeoAddress"], "lat": float(g["Latitude"]), "lon": float(g["Longitude"]),
                    "score": s["ValidationInformation"]["Score"],
                    "bname": p.get("EngPremisesAddress", {}).get("BuildingName")}
    return None


DIST_AREA = {"11": "EASTERN", "12": "WAN CHAI", "15": "SOUTHERN", "17": "ISLANDS",
             "18": "CENTRAL AND WESTERN", "51": "KWUN TONG", "52": "KOWLOON CITY",
             "53": "WONG TAI SIN", "61": "YAU TSIM MONG", "62": "YAU TSIM MONG",
             "63": "SHAM SHUI PO", "91": "KWAI TSING", "92": "TSUEN WAN", "93": "TUEN MUN",
             "94": "YUEN LONG", "95": "TAI PO", "96": "NORTH", "97": "SHA TIN", "98": "SAI KUNG"}


def query_for(street_no, street, dist, address=None):
    if street:
        return f"{street_no} {street}, {DIST_AREA.get(dist, '')}".strip(", ")
    # no street in the licence address: ask ALS with shop and floor words removed
    text = re.sub(r"\b(?:SHOPS?|UNITS?|STALLS?|KIOSKS?)\s*(?:NOS?\.?)?\s*[\w\s,&-]*?(?=,)", "", address or "")
    text = FLOOR_RE.sub("", text.upper())
    return re.sub(r"[\s,.]+", " ", text).strip()


def accept_text(body):
    """For addresses with no street: take ALS's best suggestion only if it scores 80+."""
    try:
        sugg = json.loads(body).get("SuggestedAddress", [])
    except (TypeError, json.JSONDecodeError):
        return None
    if not sugg or sugg[0]["ValidationInformation"]["Score"] < 80:
        return None
    p = sugg[0]["Address"]["PremisesAddress"]
    g = p["GeospatialInformation"]
    return {"geo": p["GeoAddress"], "lat": float(g["Latitude"]), "lon": float(g["Longitude"]),
            "score": sugg[0]["ValidationInformation"]["Score"],
            "bname": p.get("EngPremisesAddress", {}).get("BuildingName")}


# ---------------------------------------------------------------- commands

def cmd_parse(_):
    con = duckdb.connect(str(DB))
    addrs = con.execute("""SELECT address, any_value(dist) FROM spans WHERE lang='en'
                           GROUP BY address""").fetchall()
    rows = []
    for addr, dist in addrs:
        r = parse(addr)
        rows.append((addr, dist, json.dumps(r["floors"]), json.dumps(r["shops"]),
                     r["street_no"], r["street"], r["portion"]))
    con.execute("""CREATE OR REPLACE TABLE addresses (address VARCHAR, dist VARCHAR,
                   floors VARCHAR, shops VARCHAR, street_no VARCHAR, street VARCHAR, portion BOOLEAN)""")
    con.executemany("INSERT INTO addresses VALUES (?,?,?,?,?,?,?)", rows)
    print(con.execute("""SELECT count(*), count(street), count(*) FILTER (WHERE floors LIKE '%"G"%')
                         FROM addresses""").fetchall())
    con.close()


def cmd_geocode(args):
    con = duckdb.connect(str(DB), read_only=True)
    where = ""
    if args.dist:
        where = "AND dist IN (" + ",".join(f"'{d}'" for d in args.dist.split(",")) + ")"
    todo = con.execute(f"""SELECT street_no, street, dist, address FROM addresses
                           WHERE true {where}""").fetchall()
    con.close()
    db = cache()
    have = {q for (q,) in db.execute("SELECT q FROM als")}
    bodies = dict(db.execute("SELECT q, body FROM als"))
    wanted = set()
    for street_no, street, dist, address in todo:
        q = query_for(street_no, street, dist, address)
        wanted.add(q)
        if street and q in bodies and not accept(bodies[q], street, street_no):
            wanted.add(query_for(None, None, dist, address))
    qs = sorted(wanted - have - {""})
    print(f"{len(qs)} lookups to make ({len(have)} cached)", flush=True)

    def one(q):
        return q, als(q)

    n = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for q, body in ex.map(one, qs):
            if body is not None:
                db.execute("INSERT OR REPLACE INTO als VALUES (?,?,?)", (q, body, time.time()))
            n += 1
            if n % 50 == 0:
                db.commit()
                print(f"  {n}/{len(qs)}", flush=True)
    db.commit()


GOLDEN = math.pi * (3 - math.sqrt(5))


def fan(lat, lon, i, n):
    """Spread n units in one building so each can be clicked.

    A sunflower packing: evenly spaced points filling a small disc from the centre outward
    (about 4.5 m apart). A ring was used before, and big malls drew circles on the map.
    """
    if n <= 1:
        return lat, lon
    r = 0.00004 * math.sqrt(i + 0.5)
    ang = i * GOLDEN
    return lat + r * math.sin(ang), lon + r * math.cos(ang) / math.cos(math.radians(lat))


def cmd_build(_):
    con = duckdb.connect(str(DB))
    db = cache()
    bodies = dict(db.execute("SELECT q, body FROM als"))
    addrs = con.execute("SELECT * FROM addresses").fetchall()
    # address -> building
    bld = {}
    for address, dist, floors, shops, street_no, street, portion in addrs:
        body = bodies.get(query_for(street_no, street, dist, address))
        hit = accept(body, street, street_no) if street else accept_text(body)
        if street and not hit:
            hit = accept_text(bodies.get(query_for(None, None, dist, address)))
        bld[address] = hit
    # group per building+floor set to decide shop-level resolution
    groups = {}
    for address, dist, floors, shops, street_no, street, portion in addrs:
        b = bld[address]
        bkey = b["geo"] if b else f"PARSE|{street_no}|{street}" if street else f"RAW|{address}"
        groups.setdefault((bkey, floors), []).append((address, dist, json.loads(shops), portion, b))
    unit_rows, map_rows = [], []
    for (bkey, floors), items in groups.items():
        any_shop = any(s for _, _, s, _, _ in items)
        # merge addresses whose shop sets overlap into one unit (union-find)
        parent = list(range(len(items)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                si, sj = set(items[i][2]), set(items[j][2])
                if si == sj or (si & sj):
                    parent[find(i)] = find(j)
                elif any_shop and (not si or not sj):
                    # one record names no shop in a building where others do: cannot separate
                    parent[find(i)] = find(j)
        clusters = {}
        for i, it in enumerate(items):
            clusters.setdefault(find(i), []).append(it)
        for members in clusters.values():
            shop_sets = {tuple(m[2]) for m in members}
            partial = len(shop_sets) > 1
            portion = any(m[3] for m in members)
            shops = sorted({s for m in members for s in m[2]})
            b = next((m[4] for m in members if m[4]), None)
            res = "resolved" if b and not partial and not portion else "building_only"
            if not b:
                res = "not_geocoded"
            uid = f"{bkey}|{'+'.join(json.loads(floors)) or '-'}|{'+'.join(shops) or '-'}"
            unit_rows.append((uid, bkey, floors, json.dumps(shops), res,
                              b["lat"] if b else None, b["lon"] if b else None,
                              b["score"] if b else None, members[0][1]))
            for m in members:
                map_rows.append((m[0], uid))
    # fan out units sharing a building point
    by_b = {}
    for i, u in enumerate(unit_rows):
        if u[5] is not None:
            by_b.setdefault(u[1], []).append(i)
    # street-level units take the middle of the building's cluster, upper floors the outside
    for idxs in by_b.values():
        idxs.sort(key=lambda i: ("G" not in json.loads(unit_rows[i][2]), i))
    final = []
    for i, u in enumerate(unit_rows):
        lat, lon = u[5], u[6]
        if lat is not None:
            idxs = by_b[u[1]]
            lat, lon = fan(lat, lon, idxs.index(i), len(idxs))
        final.append(u[:5] + (lat, lon) + u[7:])
    con.execute("""CREATE OR REPLACE TABLE units (unit_id VARCHAR, building VARCHAR, floors VARCHAR,
                   shops VARCHAR, resolution VARCHAR, lat DOUBLE, lon DOUBLE, geocode_score DOUBLE,
                   dist VARCHAR)""")
    con.executemany("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?)", final)
    con.execute("CREATE OR REPLACE TABLE unit_addresses (address VARCHAR, unit_id VARCHAR)")
    con.executemany("INSERT INTO unit_addresses VALUES (?,?)", map_rows)
    print(con.execute("SELECT resolution, count(*) FROM units GROUP BY 1").fetchall())
    con.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse").set_defaults(fn=cmd_parse)
    g = sub.add_parser("geocode")
    g.add_argument("--dist")
    g.add_argument("--workers", type=int, default=3)
    g.set_defaults(fn=cmd_geocode)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
