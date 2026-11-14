"""Turn downloaded snapshots into dated spans in data/shopfront.duckdb.

    python pipeline/ingest.py

A span is one licence number over an unbroken run of good snapshots with an unchanged
sign, address, licence type and endorsements. A disappearance, a return, a sign change or
an address change each start a new span. Every span keeps the first and last snapshot that
support it and the first snapshot that no longer matches.

Tables written:
  snapshots   lang, snap, day, rows, status, reason
  spans       lang, licno, type, dist, sign, address, info, first_snap, last_snap,
              first_snap_not_matching, expdate_at_last, n_snaps
  langcheck   day, only_en, only_tc
  renewal_lag months, n   (licences that vanished and came back, by gap length)
"""
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

import duckdb

import gate0

ROOT = gate0.ROOT
DB = ROOT / "data" / "shopfront.duckdb"


def read_rows(path):
    for lp in ET.parse(path).getroot().iter("LP"):
        yield {
            "licno": (lp.findtext("LICNO") or "").strip(),
            "type": (lp.findtext("TYPE") or "").strip(),
            "dist": (lp.findtext("DIST") or "").strip(),
            "sign": " ".join((lp.findtext("SS") or "").split()),
            "address": " ".join((lp.findtext("ADR") or "").split()),
            "info": (lp.findtext("INFO") or "").strip(),
            "expdate": (lp.findtext("EXPDATE") or "").strip(),
        }


def manifest():
    path = ROOT / "data" / "snapshots.csv"
    if not path.exists():
        gate0.write_manifest({})
    with open(path) as f:
        return list(csv.DictReader(f))


def build_spans(lang, snaps):
    """snaps: ordered good snapshot names for one language."""
    spans, open_ = [], {}
    for i, snap in enumerate(snaps):
        nxt = snaps[i + 1] if i + 1 < len(snaps) else None
        seen = set()
        for r in read_rows(gate0.RAW / lang / f"{snap}.xml"):
            key = (r["sign"], r["address"], r["type"], r["info"])
            lic = r["licno"]
            seen.add(lic)
            cur = open_.get(lic)
            if cur and cur["key"] == key and cur["last_snap"] == snaps[i - 1]:
                cur["last_snap"], cur["expdate_at_last"] = snap, r["expdate"]
                cur["n_snaps"] += 1
                continue
            if cur:
                cur["first_snap_not_matching"] = snap
                spans.append(cur)
            open_[lic] = {
                "lang": lang, "licno": lic, "type": r["type"], "dist": r["dist"],
                "sign": r["sign"], "address": r["address"], "info": r["info"],
                "first_snap": snap, "last_snap": snap, "first_snap_not_matching": None,
                "expdate_at_last": r["expdate"], "n_snaps": 1, "key": key,
            }
        # licences missing from this snapshot close their span here
        for lic in [l for l, s in open_.items() if l not in seen and s["last_snap"] != snap]:
            s = open_.pop(lic)
            s["first_snap_not_matching"] = snap
            spans.append(s)
        if i % 20 == 0:
            print(f"  {lang} {snap}: {len(open_)} open, {len(spans)} closed", flush=True)
    spans.extend(open_.values())
    for s in spans:
        s.pop("key")
    return spans


def main():
    rows = manifest()
    con = duckdb.connect(str(DB))
    con.execute("DROP TABLE IF EXISTS snapshots")
    con.execute("""CREATE TABLE snapshots (lang VARCHAR, snap VARCHAR, day VARCHAR,
                   rows INTEGER, status VARCHAR, reason VARCHAR)""")
    con.executemany("INSERT INTO snapshots VALUES (?,?,?,?,?,?)",
                    [(r["lang"], r["snap"], r["snap"][:8], int(r["rows"]), r["status"], r["reason"])
                     for r in rows])

    cols = ["lang", "licno", "type", "dist", "sign", "address", "info", "first_snap",
            "last_snap", "first_snap_not_matching", "expdate_at_last", "n_snaps"]
    con.execute("DROP TABLE IF EXISTS spans")
    con.execute("CREATE TABLE spans (" + ", ".join(
        f"{c} {'INTEGER' if c == 'n_snaps' else 'VARCHAR'}" for c in cols) + ")")
    for lang in ("en", "tc"):
        good = sorted(r["snap"] for r in rows if r["lang"] == lang and r["status"] == "good")
        print(f"{lang}: {len(good)} good snapshots", flush=True)
        spans = build_spans(lang, good)
        con.executemany(f"INSERT INTO spans VALUES ({','.join('?' * len(cols))})",
                        [tuple(s[c] for c in cols) for s in spans])

    # English and Chinese files should hold the same licence numbers each day
    con.execute("""CREATE OR REPLACE TABLE langcheck AS
        WITH d AS (
          SELECT s.lang, n.day, s.licno FROM spans s
          JOIN snapshots n ON n.lang = s.lang AND n.status = 'good'
           AND n.snap BETWEEN s.first_snap AND s.last_snap)
        SELECT e.day,
          (SELECT count(*) FROM d x WHERE x.lang='en' AND x.day=e.day
             AND x.licno NOT IN (SELECT licno FROM d y WHERE y.lang='tc' AND y.day=e.day)) AS only_en,
          (SELECT count(*) FROM d x WHERE x.lang='tc' AND x.day=e.day
             AND x.licno NOT IN (SELECT licno FROM d y WHERE y.lang='en' AND y.day=e.day)) AS only_tc
        FROM (SELECT DISTINCT day FROM d WHERE lang='en'
              INTERSECT SELECT DISTINCT day FROM d WHERE lang='tc') e""")

    # licences that vanished and came back: how long were they missing?
    con.execute("""CREATE OR REPLACE TABLE renewal_lag AS
        WITH s AS (
          SELECT licno, first_snap_not_matching AS miss,
                 lead(first_snap) OVER (PARTITION BY licno ORDER BY first_snap) AS back
          FROM spans WHERE lang = 'en')
        SELECT round(date_diff('day', strptime(miss[1:8], '%Y%m%d'),
                                      strptime(back[1:8], '%Y%m%d')) / 30.4)::INT AS months,
               count(*) AS n
        FROM s WHERE back IS NOT NULL AND miss < back
        GROUP BY 1 ORDER BY 1""")

    q = lambda s: con.execute(s).fetchall()
    print("spans:", q("SELECT lang, count(*), count(DISTINCT licno) FROM spans GROUP BY 1"))
    print("langcheck worst days:", q("SELECT * FROM langcheck ORDER BY only_en + only_tc DESC LIMIT 3"))
    print("renewal lag (months, n):", q("SELECT * FROM renewal_lag"))
    con.close()


if __name__ == "__main__":
    main()
