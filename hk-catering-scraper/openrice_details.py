"""The details OpenRice shows only on a restaurant's own page.

    python openrice_details.py                    # every listing in out/openrice_latest.csv
    python openrice_details.py --open-only        # leave out closed and moved listings
    python openrice_details.py --district Jordan --limit 50

Run openrice.py first; this reads its CSV for the listings and their page addresses. Each
page is fetched once and what it carries is saved in data/openrice_details/<poi id>.json.gz,
so a run that stops can be started again and only fetches what is missing. The result is
out/openrice_details.csv, one row per listing, to be joined to openrice_latest.csv on poi_id.

Added here: seat count, the restaurant's description, the price range in dollars, facilities
(outdoor seating, service charge, corkage, ...), payment methods by name, the five rating
parts, popular dishes with prices, nearest MTR exit, social links and booking totals.

OpenRice puts a security check in front of these pages when they are asked for quickly.
The run stops as soon as it meets the check, keeping everything fetched so far; start it
again later to continue. Raise --pause if it stops often.

Standard library only; Python 3.9 or newer. One request per listing, one at a time: about
33,000 requests and 30 GB of transfer for all of Hong Kong.
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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "openrice_details"
OUT = ROOT / "out"
LISTINGS = OUT / "openrice_latest.csv"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
STATE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*")
# other users' profiles and live table availability are not kept
DROP = ("bookmarkedUsers", "firstReviewUser", "tmBookingWidget", "shareMessages")

COLS = ["poi_id", "name", "seats", "description", "price_min", "price_max", "facilities",
        "payments", "score_1", "score_2", "score_3", "score_4", "score_5", "ok_reviews",
        "popular_dishes", "nearest_exit", "hours_text", "hours_note", "open_late",
        "landmark_ids", "chain_listings", "menu_photos", "facebook", "instagram",
        "seats_booked", "last_booking", "collected"]


def get_page(url):
    """The page's HTML, or None when OpenRice has no such page."""
    for attempt in range(6):
        try:
            req = urllib.request.Request(urllib.parse.quote(url, safe=":/"), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} for {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(5 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 6 tries: {url}")


def extract(html):
    """What the page's embedded data says about the restaurant, or None if it has none."""
    m = STATE.search(html or "")
    if not m:
        return None
    try:
        state, _ = json.JSONDecoder().raw_decode(html[m.end():])
        services = state["services"]
        page = services["PoiDetailPage"]["services"]
        detail = dict(page["poiDetail"]["state"]["data"])
    except (ValueError, KeyError, TypeError):
        return None
    for k in DROP:
        detail.pop(k, None)
    return {
        "detail": detail,
        "header": services.get("PoiCommonService", {}).get("state", {}).get("poiHeader") or {},
        "booked": (page.get("poiBookedInfo", {}).get("state") or {}).get("_rawData") or {},
        "collected": date.today().isoformat(),
    }


def fetch(listing):
    """Save one listing's details. False means OpenRice answered with its security check."""
    path = RAW / f"{listing['poi_id']}.json.gz"
    html = get_page(listing["page"])
    found = extract(html)
    if found is None and html and "Security Check" in html:
        return False
    found = found or {"missing": True}
    tmp = path.with_suffix(".part")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(found, f, ensure_ascii=False)
    tmp.rename(path)
    return True


def one_line(s):
    return " ".join(str(s or "").split())


def names(items):
    return "|".join(one_line(i["name"]) for i in items or [] if i.get("name"))


def row(poi_id, saved):
    d, h, b = saved["detail"], saved["header"], saved["booked"]
    more = d.get("poiDetail") or {}
    return {
        "poi_id": poi_id, "name": one_line(d.get("name")),
        "seats": more.get("seatCount") or "", "description": one_line(d.get("info")),
        "price_min": d.get("priceMin") or "",
        "price_max": d.get("priceMax") if d.get("priceMax") and d["priceMax"] < 2 ** 31 - 1 else "",
        "facilities": names(d.get("conditions")), "payments": names(d.get("payments")),
        **{f"score_{n}": round(h[f"score{n}"], 2) if h.get(f"score{n}") else "" for n in range(1, 6)},
        "ok_reviews": d.get("scoreOk") if d.get("scoreOk") is not None else "",
        "popular_dishes": "|".join(
            one_line(p["name"]) + (f" (${p['price']:g})" if p.get("price") else "")
            for p in d.get("popularDishes") or [] if p.get("name")),
        "nearest_exit": one_line(more.get("nearbyStationExit") or more.get("direction")),
        "hours_text": one_line(more.get("hourInfo")), "hours_note": one_line(more.get("otherHourInfo")),
        "open_late": 1 if more.get("openLate") else "",
        "landmark_ids": "|".join(str(i) for i in d.get("landmarkIds") or []),
        "chain_listings": d.get("chainPoiCount") or "", "menu_photos": d.get("menuPhotoCount") or "",
        "facebook": d.get("facebook") or "", "instagram": d.get("instagram") or "",
        "seats_booked": b.get("bookingSeatCount") or "", "last_booking": (b.get("lastBookingTime") or "")[:10],
        "collected": saved["collected"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--open-only", action="store_true", help="skip closed and moved listings")
    ap.add_argument("--district", nargs="+", help="district names as in openrice_latest.csv")
    ap.add_argument("--limit", type=int, help="fetch at most this many pages this run")
    ap.add_argument("--pause", type=float, default=5.0, help="average seconds between pages")
    args = ap.parse_args()

    if not LISTINGS.exists():
        raise SystemExit(f"{LISTINGS} not found: run openrice.py first")
    with open(LISTINGS, encoding="utf-8-sig") as f:
        listings = [r for r in csv.DictReader(f) if r["page"]]
    if args.open_only:
        listings = [r for r in listings if r["status"] == "10"]
    if args.district:
        wanted = {n.lower() for n in args.district}
        listings = [r for r in listings if r["district"].lower() in wanted]

    RAW.mkdir(parents=True, exist_ok=True)
    todo = [r for r in listings if not (RAW / f"{r['poi_id']}.json.gz").exists()][:args.limit]
    print(f"{len(listings)} listings, {len(todo)} pages to fetch", flush=True)
    for n, r in enumerate(todo, 1):
        if not fetch(r):
            print(f"stopped by OpenRice's security check after {n - 1} pages; run again later", flush=True)
            break
        if n % 100 == 0 or n == len(todo):
            print(f"  {n}/{len(todo)}", flush=True)
        time.sleep(random.uniform(0.5, 1.5) * args.pause)

    rows, missing = [], 0
    for r in listings:
        path = RAW / f"{r['poi_id']}.json.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt", encoding="utf-8") as f:
            saved = json.load(f)
        if saved.get("missing"):
            missing += 1
        else:
            rows.append(row(r["poi_id"], saved))
    with open(OUT / "openrice_details.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} listings -> {OUT / 'openrice_details.csv'}"
          + (f" ({missing} pages had no details)" if missing else ""))


if __name__ == "__main__":
    sys.exit(main())
