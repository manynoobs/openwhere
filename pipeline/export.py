"""Write the files the map app loads, for the demo district only.

    python pipeline/export.py        # after histories.py and cuisine.py;
                                     # then run facilities.py and heat.py

web/public/data/
  units.geojson      one point per unit, slim properties (see web/src/types.ts UnitProps)
  units/<id>.json    full sign history and records for one unit, loaded on click
  search.json        address and sign index for the search box
  meta.json          file counts, coverage, heat image bounds and colour stops
"""
import csv
import json
import shutil
from datetime import date

import duckdb

from ingest import DB, ROOT

DISTRICTS = ["61"]  # Yau Tsim: Tsim Sha Tsui, Jordan, Yau Ma Tei
YEARS = list(range(2016, 2027))
OUT = ROOT / "web" / "public" / "data"


def year_ref(y, latest):
    """The snapshot that stands for the end of year y: the December file, or the latest."""
    return min(date(y, 12, 1), latest)


def listed_flags(rec, latest):
    out = []
    for y in YEARS:
        ref = year_ref(y, latest)
        started = [h for h in rec["sign_histories"] if date.fromisoformat(h["first_seen"]) <= ref]
        if not started:
            out.append("0")
            continue
        active = any(date.fromisoformat(h["last_seen"]) >= ref.replace(day=1) for h in started)
        out.append("1" if active else "2")
    return "".join(out)


def change_digits(rec):
    return "".join(str(min(9, sum(1 for c in rec["changes"] if c["year"] <= y))) for y in YEARS)


def last_sign(rec):
    h = rec["sign_histories"][-1]
    for s in reversed(h["signs"]):
        names = [n for n in (s["tc"], s["en"]) if n and "記錄" not in n and "紀錄" not in n
                 and "record" not in n.lower()]
        if names:
            return " · ".join(dict.fromkeys(names))
    return ""


def main():
    recs = [json.loads(l) for l in open(ROOT / "data" / "histories.jsonl")]
    recs = [r for r in recs if r["dist"] in DISTRICTS and r["lat"] is not None]
    recs.sort(key=lambda r: r["unit_id"])
    latest = date.fromisoformat(recs[0]["latest_file"])

    if OUT.exists():
        shutil.rmtree(OUT / "units", ignore_errors=True)
    (OUT / "units").mkdir(parents=True, exist_ok=True)

    cuisine_path = ROOT / "data" / "cuisine.json"
    cuisine = json.load(open(cuisine_path)) if cuisine_path.exists() else {}
    features, search = [], []
    for i, r in enumerate(recs, start=1):
        sl = 1 if r["street_level"] else 0
        props = {
            "id": i,
            "en": r["address_en"],
            "tc": r["address_tc"] or "",
            "s": last_sign(r),
            "chg": r["store_changes"],
            "c": change_digits(r),
            "l": listed_flags(r, latest),
            "res": "b" if r["resolution"] != "resolved" or r["shared"] else "r",
            "t": r["lic_type_now"] or (r["lic_types_ever"][-1] if r["lic_types_ever"] else ""),
            "rr": 1 if r["lic_types_ever"] == ["RR"] else 0,
            "seat": 1 if r["outside_seating_ever"] else 0,
            "sl": sl,
            "d": r["dist"],
            # cuisine guessed from the current sign (pipeline/cuisine.py); only for shops listed now
            "cu": cuisine.get(r["unit_id"], "") if r["listed_now"] else "",
        }
        features.append({"type": "Feature", "id": i,
                         "geometry": {"type": "Point", "coordinates": [round(r["lon"], 6), round(r["lat"], 6)]},
                         "properties": props})
        signs = sorted({n for h in r["sign_histories"] for s in h["signs"] for n in (s["en"], s["tc"]) if n})
        search.append([i, r["address_en"], r["address_tc"] or "", " | ".join(signs), r["store_changes"],
                       round(r["lon"], 6), round(r["lat"], 6)])
        detail = {k: v for k, v in r.items() if k not in ("geocode_score",)}
        detail["id"] = i
        detail["cuisine"] = props["cu"] or None
        with open(OUT / "units" / f"{i}.json", "w") as f:
            json.dump(detail, f, ensure_ascii=False, separators=(",", ":"))

    with open(OUT / "units.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False,
                  separators=(",", ":"))
    with open(OUT / "search.json", "w") as f:
        json.dump(search, f, ensure_ascii=False, separators=(",", ":"))

    snaps = list(csv.DictReader(open(ROOT / "data" / "snapshots.csv")))
    con = duckdb.connect(str(DB), read_only=True)
    lag = con.execute("SELECT months, n FROM renewal_lag ORDER BY months").fetchall()
    con.close()
    all_dist = [json.loads(l) for l in open(ROOT / "data" / "histories.jsonl")]
    street_all = [r for r in all_dist if r["dist"] in DISTRICTS and r["street_level"]]
    meta_path = OUT / "meta.json"
    meta = json.load(open(meta_path)) if meta_path.exists() else {}
    meta.update({
        "district": "Yau Tsim",
        "district_detail": "Tsim Sha Tsui, Jordan and Yau Ma Tei (FEHD district 61)",
        "first_file": recs[0]["first_file"],
        "latest_file": recs[0]["latest_file"],
        "files_good": sum(s["status"] == "good" for s in snaps),
        "files_quarantined": sum(s["status"] != "good" for s in snaps),
        "versions_in_archive": 3828,
        "units": len(features),
        "units_street_level": sum(f["properties"]["sl"] for f in features),
        "street_units_total": len(street_all),
        "street_units_mapped": sum(1 for r in street_all if r["lat"] is not None),
        "units_resolved": sum(1 for f in features if f["properties"]["res"] == "r"),
        "renewal_lag": {"months": [m for m, _ in lag], "n": [n for _, n in lag]},
        "gap_threshold_months": 6,
        "generated": date.today().isoformat(),
    })
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"{len(features)} units exported to {OUT}")


if __name__ == "__main__":
    main()
