"""Private clinics, day procedure centres and hospitals in Hong Kong, from the Department of
Health's Private Healthcare Facilities Register.

    python orphf.py                      # hospitals, day procedure centres, clinics, nursing homes
    python orphf.py --type DPC C         # some kinds only
    python orphf.py --type SPC           # small practice clinics

The register lists the premises licensed or exempted under the Private Healthcare Facilities
Ordinance (Cap. 633):

  PH    Private Hospital          licensed
  DPC   Day Procedure Centre      licensed; surgery, endoscopy, chemotherapy and the like
  C     Clinic                    licensed
  SPC   Small Practice Clinic     exempted; run by the doctors or dentists who practise there
  NH    Scheduled Nursing Home    exempted

Its search answers 15 facilities a request, in English or Chinese, so each kind is walked in
name order in both languages and joined on the facility number. Every answer is saved as it
arrives in data/orphf/<date>/, so a run that stops can be started again the same day and picks
up where it left off. The CSV is built from every answer saved that day.

The register answers with an error page for any 15 that include a record it cannot show. The
walk steps around such a record, and the closing count shows it as missing.

Small practice clinics are registered under the name of the doctor or dentist who runs them,
so they are collected only when asked for.

E-mail addresses on the register are not kept.

Standard library only; Python 3.9 or newer. A run is about 115 requests and takes around five
minutes; the 3,072 small practice clinics are another 410 requests and 20 minutes.
"""
import argparse
import csv
import gzip
import http.cookiejar
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "orphf"
OUT = ROOT / "out"
REGISTER = "https://www.directory.orphf.gov.hk/Directory"
TYPES = {"PH": "Private Hospital", "DPC": "Day Procedure Centre", "C": "Clinic",
         "SPC": "Small Practice Clinic", "NH": "Scheduled Nursing Home"}
PAGE = 15  # facilities in one answer, whatever length is asked for
SEARCH_FIELDS = ("HighlightKeyword", "Name", "PHFType", "District", "PracticeType", "SpecialService")
COLS = ["phf_no", "type", "name_en", "name_tc", "address_en", "address_tc", "district",
        "phone", "collected"]


def get(url, open_):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hk-places-scraper/0.1"})
            with open_(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise SystemExit(f"HTTP {e.code} from {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(20 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {url}")


def chinese_session():
    """The register serves Chinese only to a session that has switched language."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    q = urllib.parse.urlencode({"strNewLang": "tc", "strReturnUrl": "/Directory/en/Home/Home", "form": "[]"})
    get(f"{REGISTER}/en/Home/ChangeLanguage?{q}", opener.open)
    time.sleep(1 + random.random())
    return opener.open


def window(day, lang, kind, start, open_, direction="asc"):
    """Facilities `start` to `start + 14` of one kind in name order, from disk if saved today.
    None when the register answers with its error page."""
    path = day / f"{kind}_{lang}_{direction}_{start:05d}.json.gz"
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    model = json.dumps([{"name": f, "value": kind if f == "PHFType" else ""} for f in SEARCH_FIELDS])
    q = urllib.parse.urlencode({"draw": 1, "start": start, "length": PAGE, "order[0][column]": 1,
                                "order[0][dir]": direction, "dataModel": model, "loadingTimes": 0})
    raw = get(f"{REGISTER}/{lang}/Home/DesktopResult?{q}", open_)
    time.sleep(1 + random.random())
    if not raw.lstrip().startswith(b"{"):
        return None
    answer = json.loads(raw)
    for facility in answer["data"]:
        facility.pop("Email", None)
    tmp = path.with_suffix(".part")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(answer, f, ensure_ascii=False)
    tmp.rename(path)
    return answer


def walk(day, lang, kind, open_):
    """Save every facility of one kind. Where a window comes back as the error page, find the
    first window after the record that causes it, read the facilities just before that record
    from the list in descending order, and carry on."""
    pos, total = 0, 1
    while pos < total:
        answer = window(day, lang, kind, pos, open_)
        if answer is None:
            lo, hi = pos + 1, pos + PAGE
            while lo < hi:
                mid = (lo + hi) // 2
                if window(day, lang, kind, mid, open_) is None:
                    lo = mid + 1
                else:
                    hi = mid
            answer = window(day, lang, kind, lo, open_)
            if answer is None:
                raise SystemExit("the register is answering with its error page; start again later")
            if lo - 1 > pos:
                window(day, lang, kind, answer["recordsTotal"] - lo + 1, open_, "desc")
            pos = lo
        total = answer["recordsTotal"]
        pos += PAGE
        if pos // PAGE % 20 == 0:
            print(f"  {kind} {lang} {min(pos, total)}/{total}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--type", nargs="+", choices=list(TYPES), default=["PH", "DPC", "C", "NH"])
    args = ap.parse_args()
    today = date.today().isoformat()
    day = RAW / today.replace("-", "")
    day.mkdir(parents=True, exist_ok=True)
    for kind in args.type:
        walk(day, "en", kind, urllib.request.urlopen)
    chinese = chinese_session()
    for kind in args.type:
        walk(day, "tc", kind, chinese)

    def saved(lang):
        for p in sorted(day.glob(f"*_{lang}_*.json.gz")):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                yield p.name.split("_")[0], json.load(f)

    tc = {f["PHFNo"]: f for _, answer in saved("tc") for f in answer["data"]}
    rows, listed = {}, {}
    for kind, answer in saved("en"):
        listed[kind] = answer["recordsTotal"]
        for f in answer["data"]:
            t = tc.get(f["PHFNo"], {})
            address = f["Address"][0]["Address"] if f["Address"] else ""
            parts = [p.strip() for p in address.split(",")]
            rows[f["PHFNo"]] = {
                "phf_no": f["PHFNo"], "type": TYPES[kind],
                "name_en": f["PHFName"], "name_tc": t.get("PHFName", ""),
                "address_en": address,
                "address_tc": t["Address"][0]["Address"] if t.get("Address") else "",
                "district": parts[-2].removesuffix(" DISTRICT").title() if len(parts) > 1 else "",
                "phone": " / ".join(x for x in (f["PhoneNo"], f["PhoneNo2"]) if x),
                "collected": today,
            }
    rows = sorted(rows.values(), key=lambda r: r["phf_no"])
    OUT.mkdir(exist_ok=True)
    with open(OUT / "orphf.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    have = Counter(r["type"] for r in rows)
    for kind, total in listed.items():
        print(f"{have[TYPES[kind]]:6} of {total:5}  {TYPES[kind]}")
    print(f"{len(rows)} facilities -> {OUT / 'orphf.csv'}")


if __name__ == "__main__":
    sys.exit(main())
