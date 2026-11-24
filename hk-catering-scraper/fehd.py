"""Hong Kong food-business licences from the Food and Environmental Hygiene Department.

    python fehd.py latest                         # today's lists -> out/fehd_latest.csv
    python fehd.py history --start 2016-01-01     # archived monthly lists since then
    python fehd.py spans                          # out/fehd_spans.csv from every list on disk
    python fehd.py positions                      # give the licences a map position

Four public lists are read, each in English and Chinese:
  restaurant   general, light refreshment and marine restaurant licences
  food         food factory, bakery, siu mei, fresh provision, factory canteen and others
  permit       restricted-food permits (sushi, oysters, frozen confections, ...)
  liquor       liquor licences and club liquor licences, with the permitted head-count
               where the licence states one

Downloaded lists are kept in data/raw/<source>/<lang>/YYYYMMDD-HHMM.xml. `latest` adds
today's; `history` adds past ones from the DATA.GOV.HK historical archive (daily versions
since 2016, liquor since November 2019). `spans` turns them into one row per licence per
unbroken run with the same name, address and type, so openings, closures and name changes
can be dated.

`positions` reads the map position the department publishes for every restaurant, food and
liquor licence in force (point data on portal.csdi.gov.hk, joined by licence number), keeps
it in data/positions.json and writes both CSVs again with `lat`, `lon` and `placed_by`:
`licence` when the position is the licence's own, `address` when it is that of another
licence at the same written address. Positions are kept from run to run, so a licence that
later lapses keeps the one it had. Permits have no published position.

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
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "out"
ARCHIVE = "https://api.data.gov.hk/v1/historical-archive"
POINTS = "https://portal.csdi.gov.hk/csdi-webpage/file-api"
POSITIONS = ROOT / "data" / "positions.json"
HOST = "www.fehd.gov.hk"
TEXT = "licensing/license/text"
SOURCES = {
    "restaurant": {"en": f"english/{TEXT}/LP_Restaurants_EN.XML", "tc": f"tc_chi/{TEXT}/LP_Restaurants_TC.XML"},
    "food": {"en": f"english/{TEXT}/LP_OtherFood_EN.XML", "tc": f"tc_chi/{TEXT}/LP_OtherFood_TC.XML"},
    "permit": {"en": f"english/{TEXT}/LP_Permits_EN.XML", "tc": f"tc_chi/{TEXT}/LP_Permits_TC.XML"},
    "liquor": {"en": f"english/{TEXT}/edatabase_liquor.xml", "tc": f"tc_chi/{TEXT}/database_liquor.xml"},
}
POINT_LISTS = {  # source: (dataset id, layer) on the CSDI portal
    "restaurant": ("fehd_rcd_1630036390312_58893", "FEHD_RL"),
    "food": ("fehd_rcd_1630036111498_75446", "FEHD_FL"),
    "liquor": ("fehd_rcd_1695972959083_79626", "FEHD_LL"),
}
CAPACITY = re.compile(r"Not more than\s*\(?\s*(\d+)\s*\)?\s*persons", re.I)

LATEST_COLS = ["source", "licence_no", "type_code", "type", "district_code", "district",
               "name_en", "name_tc", "address_en", "address_tc", "info_codes", "expiry",
               "capacity", "list_date", "lat", "lon", "placed_by"]
SPAN_COLS = ["source", "licence_no", "type_code", "type", "district_code", "district",
             "name_en", "name_tc", "address_en", "address_tc",
             "first_seen", "last_seen", "gone_by", "lists", "lat", "lon", "placed_by"]


def http_get(url, tries=6):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hk-catering-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** attempt + random.random())
                continue
            raise SystemExit(f"HTTP {e.code} for {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 ** attempt + random.random())
    raise SystemExit(f"network error after {tries} tries: {url}")


def save(source, lang, stamp, data):
    out = RAW / source / lang / f"{stamp}.xml"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.rename(out)
    return out


def clean(s):
    return " ".join((s or "").split())


def parse(path):
    """Return (codes, rows): code tables by field, and one dict per licence."""
    root = ET.parse(path).getroot()
    codes = {t.tag[:-5]: {c.get("ID"): clean(c.text) for c in t}
             for t in root if t.tag.endswith("_CODE")}
    rows = [{f.tag: (f.text or "") for f in lp} for lp in root.iter() if lp.find("LICNO") is not None]
    return codes, rows


def records(en_path, tc_path):
    """Licences of one list, English joined to Chinese by licence number."""
    codes, en = parse(en_path)
    tc = {r["LICNO"].strip(): r for r in parse(tc_path)[1]} if tc_path else {}
    for r in en:
        lic = r["LICNO"].strip()
        t = tc.get(lic, {})
        coded = "TYPE" in r  # the liquor list spells type and district out instead
        cap = CAPACITY.search(r.get("ALC", ""))
        yield {
            "licence_no": lic,
            "type_code": r["TYPE"].strip() if coded else "",
            "type": codes.get("TYPE", {}).get(r["TYPE"].strip(), "") if coded else clean(r.get("LICTYPE")),
            "district_code": r["DIST"].strip() if coded else "",
            "district": codes.get("DIST", {}).get(r["DIST"].strip(), "") if coded else clean(r.get("DIST")),
            "name_en": clean(r.get("SS")), "name_tc": clean(t.get("SS")),
            "address_en": clean(r.get("ADR")), "address_tc": clean(t.get("ADR")),
            "info_codes": clean(r.get("INFO")),
            "expiry": clean(r.get("EXPDATE") or r.get("LVU")),
            "capacity": cap.group(1) if cap else "",
        }


def write_csv(path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel reads the Chinese
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def place(rows):
    """Fill lat, lon and placed_by from the saved positions."""
    positions = json.loads(POSITIONS.read_text()) if POSITIONS.exists() else {}
    written = lambda r: "".join(r["address_tc"].split())
    at_address = {}
    for r in rows:
        r["at"] = positions.get(r["source"], {}).get(r["licence_no"])
        if r["at"] and r["address_tc"]:
            at_address.setdefault(written(r), r["at"])
    for r in rows:
        at = r.pop("at")
        by = "licence" if at else "address" if written(r) in at_address else ""
        r["lat"], r["lon"] = at or at_address.get(written(r), ("", ""))
        r["placed_by"] = by
    return rows


def iso(stamp):
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def cmd_latest(args):
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    rows = []
    for source in args.source:
        paths = {lang: save(source, lang, stamp, http_get(f"https://{HOST}/{p}"))
                 for lang, p in SOURCES[source].items()}
        mine = [{"source": source, "list_date": iso(stamp), **r} for r in records(paths["en"], paths["tc"])]
        print(f"{source}: {len(mine)} licences")
        rows += mine
    write_csv(OUT / "fehd_latest.csv", LATEST_COLS, place(rows))
    print(f"{len(rows)} rows -> {OUT / 'fehd_latest.csv'}")


def versions(source, lang, start, end):
    """Archived versions as {stamp: url}. The archive files them under http:// in its
    early years and https:// later, so both are asked."""
    found = {}
    for scheme in ("http", "https"):
        url = f"{scheme}://{HOST}/{SOURCES[source][lang]}"
        q = urllib.parse.urlencode({"url": url, "start": start, "end": end})
        for ts in json.loads(http_get(f"{ARCHIVE}/list-file-versions?{q}"))["timestamps"]:
            found.setdefault(ts, url)
    return found


def first_per(stamps, step):
    seen, out = set(), []
    for ts in sorted(stamps):
        d = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
        key = {"monthly": (d.year, d.month), "weekly": d.isocalendar()[:2], "daily": d}[step]
        if key not in seen:
            seen.add(key)
            out.append(ts)
    return out


def cmd_history(args):
    start = args.start.replace("-", "")
    end = (args.end or (date.today() - timedelta(days=1)).isoformat()).replace("-", "")
    jobs = []
    for source in args.source:
        en, tc = (versions(source, lang, start, end) for lang in ("en", "tc"))
        tc_day = {ts[:8]: ts for ts in sorted(tc, reverse=True)}
        for ts in first_per(en, args.step):  # pair by day so both languages describe one list
            if ts[:8] in tc_day:
                jobs += [(source, "en", ts, en[ts]), (source, "tc", tc_day[ts[:8]], tc[tc_day[ts[:8]]])]
        print(f"{source}: {len(en)} versions in the archive", flush=True)
    jobs = [j for j in jobs if not (RAW / j[0] / j[1] / f"{j[2]}.xml").exists()]
    print(f"{len(jobs)} files to download ({args.step})", flush=True)

    def fetch(job):
        source, lang, ts, url = job
        time.sleep(random.uniform(0.2, 0.8))
        q = urllib.parse.urlencode({"url": url, "time": ts})
        save(source, lang, ts, http_get(f"{ARCHIVE}/get-file?{q}"))

    with ThreadPoolExecutor(max_workers=3) as ex:
        for n, _ in enumerate(ex.map(fetch, jobs), 1):
            if n % 20 == 0:
                print(f"  {n}/{len(jobs)}", flush=True)


def good_lists(source):
    """Yield (stamp, records) for each day on disk with a usable English and Chinese list.
    A list is skipped if it does not parse, repeats a licence number, or has lost more than
    8% of its rows against the previous good one: read as real, a cut-off file would look
    like hundreds of closures."""
    tc_day = {p.stem[:8]: p for p in sorted((RAW / source / "tc").glob("*.xml"), reverse=True)}
    prev, last_day = None, None
    for en in sorted((RAW / source / "en").glob("*.xml")):
        day = en.stem[:8]
        if day == last_day or day not in tc_day:
            continue
        try:
            recs = list(records(en, tc_day[day]))
        except ET.ParseError as e:
            print(f"  skipped {source} {en.stem}: {e}")
            continue
        n = len(recs)
        if n == 0 or len({r["licence_no"] for r in recs}) != n or (prev and n < prev * 0.92):
            print(f"  skipped {source} {en.stem}: {n} rows after {prev}")
            continue
        prev, last_day = n, day
        yield en.stem, recs


def build_spans(source):
    keys = ("type_code", "name_en", "name_tc", "address_en", "address_tc")
    done, open_, before = [], {}, None
    for stamp, recs in good_lists(source):
        seen = set()
        for r in recs:
            lic = r["licence_no"]
            seen.add(lic)
            cur = open_.get(lic)
            if cur and cur["last"] == before and all(cur[k] == r[k] for k in keys):
                cur["last"] = stamp
                cur["lists"] += 1
                continue
            if cur:
                cur["gone"] = stamp
                done.append(cur)
            open_[lic] = {**r, "source": source, "first": stamp, "last": stamp, "gone": "", "lists": 1}
        for lic in [l for l in open_ if l not in seen]:
            s = open_.pop(lic)
            s["gone"] = stamp
            done.append(s)
        before = stamp
    done += open_.values()
    for s in done:
        s["first_seen"], s["last_seen"] = iso(s["first"]), iso(s["last"])
        s["gone_by"] = iso(s["gone"]) if s["gone"] else ""
    return sorted(done, key=lambda s: (s["licence_no"], s["first"]))


def cmd_spans(args):
    rows = []
    for source in args.source:
        mine = build_spans(source)
        still = sum(1 for s in mine if not s["gone_by"])
        print(f"{source}: {len(mine)} spans, {len({s['licence_no'] for s in mine})} licences, "
              f"{still} on the newest list")
        rows += mine
    write_csv(OUT / "fehd_spans.csv", SPAN_COLS, place(rows))
    print(f"{len(rows)} rows -> {OUT / 'fehd_spans.csv'}")


def cmd_positions(args):
    positions = json.loads(POSITIONS.read_text()) if POSITIONS.exists() else {}
    today = date.today().strftime("%Y%m%d")
    for source, (dataset, layer) in POINT_LISTS.items():
        q = urllib.parse.urlencode({"dataset_id": dataset, "format": "geojson", "layer_name": layer})
        body = http_get(f"{POINTS}?{q}")
        out = RAW.parent / "positions" / f"{today}_{source}.geojson.gz"
        out.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(out, "wb") as f:
            f.write(body)
        features = json.loads(body)["features"]
        for feature in features:
            lon, lat = feature["geometry"]["coordinates"][:2]
            positions.setdefault(source, {})[feature["properties"]["SEARCH02_EN"]] = [lat, lon]
        print(f"{source}: {len(features)} positions")
        time.sleep(1)
    POSITIONS.write_text(json.dumps(positions))
    for name, cols in (("fehd_latest.csv", LATEST_COLS), ("fehd_spans.csv", SPAN_COLS)):
        if (OUT / name).exists():
            with open(OUT / name, encoding="utf-8-sig", newline="") as f:
                rows = place(list(csv.DictReader(f)))
            write_csv(OUT / name, cols, rows)
            how = Counter(r["placed_by"] for r in rows)
            print(f"{name}: {how['licence']} placed by licence, {how['address']} by address, "
                  f"{how['']} without a position")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("positions").set_defaults(fn=cmd_positions)
    for name, fn in (("latest", cmd_latest), ("history", cmd_history), ("spans", cmd_spans)):
        p = sub.add_parser(name)
        p.add_argument("--source", nargs="+", choices=list(SOURCES), default=list(SOURCES))
        p.set_defaults(fn=fn)
        if name == "history":
            p.add_argument("--start", default="2016-01-01", help="YYYY-MM-DD")
            p.add_argument("--end", help="YYYY-MM-DD, default yesterday")
            p.add_argument("--step", choices=["monthly", "weekly", "daily"], default="monthly")
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
