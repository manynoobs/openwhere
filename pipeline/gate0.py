"""Download FEHD restaurant licence snapshots from the DATA.GOV.HK historical archive.

    python pipeline/gate0.py probe
    python pipeline/gate0.py pull --step monthly   # first good version of each month, EN + TC
    python pipeline/gate0.py pull --step weekly

Files land in data/raw/{en,tc}/YYYYMMDD-HHMM.xml. A file is validated as it arrives and
quarantined (kept, never interpreted) if it is truncated, lacks a field, repeats a licence
number, or its row count drops more than 8% against the previous good file.
data/snapshots.csv keeps three numbers apart: versions in the archive, files downloaded,
files parsed as good.
"""
import argparse
import csv
import json
import random
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
API = "https://api.data.gov.hk/v1/historical-archive"
# The archive indexes these files under http:// until 28 May 2021 and under https:// from
# 29 May 2021; the two ranges join without a gap, so both are listed and merged.
PATHS = {
    "en": "www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML",
    "tc": "www.fehd.gov.hk/tc_chi/licensing/license/text/LP_Restaurants_TC.XML",
}
SOURCES = {lang: [f"http://{p}", f"https://{p}"] for lang, p in PATHS.items()}
FIELDS = ("TYPE", "DIST", "LICNO", "SS", "ADR", "INFO", "EXPDATE")
START, END = "20160101", (date.today() - timedelta(days=1)).strftime("%Y%m%d")


def http_get(url, tries=6):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "shopfront-past-lives/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                time.sleep(2 ** attempt + random.random())
                continue
            body = e.read()[:300]
            raise SystemExit(f"HTTP {e.code} for {url}: {body!r}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 ** attempt + random.random())
    raise SystemExit(f"network error after {tries} tries: {url}")


URL_OF = {}  # (lang, timestamp) -> archived source URL


def list_versions(lang):
    stamps = []
    for url in SOURCES[lang]:
        q = urllib.parse.urlencode({"url": url, "start": START, "end": END})
        for ts in json.loads(http_get(f"{API}/list-file-versions?{q}"))["timestamps"]:
            URL_OF.setdefault((lang, ts), url)
            stamps.append(ts)
    return sorted(set(stamps))


def pick(stamps, step):
    """First version of each month (or ISO week)."""
    seen, out = set(), []
    for ts in sorted(stamps):
        d = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
        key = (d.year, d.month) if step == "monthly" else d.isocalendar()[:2]
        if key not in seen:
            seen.add(key)
            out.append(ts)
    return out


def validate(path):
    """Return (row_count, reason). reason is None for a good file."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        return 0, f"truncated or malformed XML: {e}"
    rows = root.iter("LP")
    licnos, n = set(), 0
    for lp in rows:
        n += 1
        for f in ("TYPE", "DIST", "LICNO", "SS", "ADR"):
            if lp.find(f) is None:
                return n, f"missing field {f} in row {n}"
        lic = lp.findtext("LICNO")
        if lic in licnos:
            return n, f"duplicate licence number {lic}"
        licnos.add(lic)
    if n == 0:
        return 0, "no rows"
    return n, None


def fetch(lang, ts):
    out = RAW / lang / f"{ts}.xml"
    if out.exists() and out.stat().st_size > 0:
        return out
    time.sleep(random.uniform(0.2, 0.8))
    q = urllib.parse.urlencode({"url": URL_OF[(lang, ts)], "time": ts})
    data = http_get(f"{API}/get-file?{q}")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.rename(out)
    return out


def write_manifest(versions):
    rows = []
    for lang in SOURCES:
        prev = None
        for p in sorted((RAW / lang).glob("*.xml")):
            n, reason = validate(p)
            if reason is None and prev and n < prev * 0.92:
                reason = f"row count fell {prev} -> {n} (more than 8%)"
            status = "good" if reason is None else "quarantined"
            if status == "good":
                prev = n
            rows.append({"lang": lang, "snap": p.stem, "rows": n, "status": status, "reason": reason or ""})
    with open(ROOT / "data" / "snapshots.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lang", "snap", "rows", "status", "reason"])
        w.writeheader()
        w.writerows(rows)
    for lang in SOURCES:
        mine = [r for r in rows if r["lang"] == lang]
        good = sum(r["status"] == "good" for r in mine)
        print(f"{lang}: {len(versions.get(lang, []))} versions in archive, "
              f"{len(mine)} downloaded, {good} parsed as good")


def cmd_probe(_):
    v = {lang: list_versions(lang) for lang in SOURCES}
    days = {lang: {ts[:8] for ts in v[lang]} for lang in v}
    print({lang: len(v[lang]) for lang in v})
    print("first/last EN:", v["en"][0], v["en"][-1])
    only_en, only_tc = days["en"] - days["tc"], days["tc"] - days["en"]
    print(f"days only in EN: {len(only_en)}, only in TC: {len(only_tc)}")
    print("PROBE: PASS" if v["en"] and v["tc"] else "PROBE: FAIL")


def cmd_pull(args):
    versions = {lang: list_versions(lang) for lang in SOURCES}
    # pair by day so EN and TC describe the same list
    tc_by_day = {ts[:8]: ts for ts in sorted(versions["tc"], reverse=True)}
    jobs = []
    for ts in pick(versions["en"], args.step):
        jobs.append(("en", ts))
        if ts[:8] in tc_by_day:
            jobs.append(("tc", tc_by_day[ts[:8]]))
    print(f"{len(jobs)} files to fetch ({args.step})", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        for _ in ex.map(lambda j: fetch(*j), jobs):
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
    write_manifest(versions)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe").set_defaults(fn=cmd_probe)
    p = sub.add_parser("pull")
    p.add_argument("--step", choices=["monthly", "weekly"], default="monthly")
    p.set_defaults(fn=cmd_pull)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
