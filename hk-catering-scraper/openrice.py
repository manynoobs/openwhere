"""Every OpenRice listing in Hong Kong, from the site's own search results.

    python openrice.py                      # all districts -> out/openrice_latest.csv
    python openrice.py --district "Wan Chai" Jordan
    python openrice.py --list               # district names and listing counts
    python openrice.py --rebuild            # write the CSV again from the newest run on disk

The search is walked one district at a time, 100 listings a request, because it stops
answering at large offsets across the whole city. Each district is saved as it completes in
data/openrice/<date>/<district id>.json.gz, so a run that stops can be started again and
picks up where it left off. Those files hold OpenRice's full answer for every listing; the
CSV is built from them, and a listing filed under two districts is written once.

Listings that OpenRice marks as closed or moved are included, with their status code and
the id of the listing they moved to.

`category` is "Beverage shop" for a listing OpenRice tags as a coffee shop, Taiwanese drink
shop, herbal tea shop, juice shop or tea house whose other tags are only light food
(bakery, cake, dessert, sandwich, snacks) and whose name does not say restaurant, kitchen
or a meal; a drink-tagged listing that also serves meals, and everything else, is
"Restaurant".

Standard library only; Python 3.9 or newer. A full run is about 350 requests and takes
around an hour.
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
RAW = ROOT / "data" / "openrice"
OUT = ROOT / "out"
SEARCH = "https://www.openrice.com/api/v2/search"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
ROWS = 100
REGIONS = {1999, 2999, 3999, 4999}  # whole-region entries; their districts are walked instead
PRICE = {1: "Under $50", 2: "$51-100", 3: "$101-200", 4: "$201-400", 5: "$401-800", 6: "Over $800"}
CATEGORY = {1: "cuisines", 2: "dishes", 3: "kinds"}  # OpenRice categoryTypeId
DRINKS = {"Coffee Shop", "Taiwanese Drink", "Herbal Tea", "Juice", "Tea House", "Beverages"}
LIGHT = {"Bakery", "Cake", "Cake Shop", "Dessert", "Sandwich", "Salad", "Ice Cream/yogurt",
         "Snack Shop & Deli", "Sweets", "Sweet Soup", "Chocolate/Candy Shop", "Herbal Cuisine"}
# tags that describe the place, not what it serves
TRAITS = {"Pet Friendly", "Salt & Sugar Reduction Restaurant", "Takeaway", "Food Wise Eateries",
          "Upper-floor Cafe", "Vegetarian", "Meatless Menu", "Organic Food", "Family Friendly",
          "Online Shop/ Food Distributor", "Nostalgic", "Certified Halal Food", "No Shark Fin",
          "Vending Machine", "Theme Restaurant", "Celebrity Shop", "Outdoor", "Food Court",
          "Cyber Cafe", "Party Food"}
MEAL_NAME = re.compile(r"restaurant|bistro|kitchen|diner|餐廳|廚房|便當|飯|麵|粉", re.I)
DAYS = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}  # OpenRice dayOfWeek

COLS = ["poi_id", "name_en", "name_tc", "category", "status", "status_remark", "moved_to_id",
        "district_id", "district", "address_en", "address_tc", "floor", "unit", "mall",
        "lat", "lon", "price_range_id", "price", "cuisines", "dishes", "kinds",
        "other_categories", "signature_dishes", "phones", "phone_remarks", "website",
        "open_since", "hours", "score", "smiles", "cries", "reviews", "bookmarks", "photos",
        "videos", "payment_ids", "online_booking", "booking_url", "booking_menus",
        "promotions", "coupons", "vouchers", "has_offer", "premium_menu", "queuing",
        "paid_account", "verified", "sponsored", "new_listing", "virtual", "award_status",
        "door_photo", "url", "page", "collected"]


def search(**params):
    q = urllib.parse.urlencode({"uiLang": "en", "uiCity": "hongkong", **params})
    for attempt in range(6):
        try:
            req = urllib.request.Request(f"{SEARCH}?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} for {SEARCH}?{q}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            pass
        time.sleep(5 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 6 tries: {SEARCH}?{q}")


def districts():
    found = []
    for d in search(rows=1)["refineSearchFilter"]["districts"]:
        did = int(d["searchKey"].split("=")[1])
        if did not in REGIONS:
            found.append({"id": did, "name": d["name"], "count": d["count"] or 0})
    return sorted(found, key=lambda d: d["name"])


def hours(poi_hours):
    """'Mon 08:00-21:45; Tue 11:30-15:00, 17:30-21:00; Sun closed'"""
    out = []
    for h in poi_hours or []:
        if (h.get("isHoliday") or h.get("isHolidayEve") or h.get("day") or h.get("lunarDay")
                or h.get("dayOfWeek") not in DAYS):
            continue  # special-day rows
        if h.get("isClose"):
            span = "closed"
        elif h.get("is24hr"):
            span = "24hr"
        else:
            span = ", ".join(f"{h[f'period{n}Start'][:5]}-{h[f'period{n}End'][:5]}"
                             for n in (1, 2) if h.get(f"period{n}Start") and h.get(f"period{n}End"))
        out.append(f"{DAYS[h['dayOfWeek']]} {span}")
    return "; ".join(out)


def titles(items, key="title"):
    return "|".join(" ".join(str(i[key]).split()) for i in items or [] if i.get(key))


def flag(v):
    return 1 if v else ""


def slim(p, today):
    cats = {}
    for c in p.get("categories") or []:
        cats.setdefault(CATEGORY.get(c.get("categoryTypeId"), "other_categories"), []).append(c["name"])
    d = p.get("district") or {}
    served = set(cats.get("dishes", []) + cats.get("kinds", [])) - TRAITS
    return {
        "poi_id": p["poiId"], "name_en": p.get("name") or "", "name_tc": p.get("nameOtherLang") or "",
        "category": "Beverage shop" if (
            served & DRINKS and served <= DRINKS | LIGHT
            and not MEAL_NAME.search(f"{p.get('name')} {p.get('nameOtherLang')}")) else "Restaurant",
        "status": p.get("status"), "status_remark": p.get("statusRemark") or "",
        "moved_to_id": p.get("moveToId") or "",
        "district_id": d.get("districtId"), "district": d.get("name") or "",
        "address_en": p.get("address") or "", "address_tc": p.get("addressOtherLang") or "",
        "floor": p.get("floor") or "", "unit": p.get("unit") or "", "mall": p.get("mallName") or "",
        "lat": p.get("mapLatitude"), "lon": p.get("mapLongitude"),
        "price_range_id": p.get("priceRangeId") or "", "price": PRICE.get(p.get("priceRangeId"), ""),
        **{k: "|".join(cats.get(k, [])) for k in ("cuisines", "dishes", "kinds", "other_categories")},
        "signature_dishes": titles(p.get("tags"), "name"),
        "phones": "|".join(p.get("phones") or []),
        "phone_remarks": "|".join(r for r in p.get("phoneRemarks") or [] if r),
        "website": p.get("website") or "",
        "open_since": (p.get("openSince") or "")[:10], "hours": hours(p.get("poiHours")),
        "score": round(p["scoreOverall"], 2) if p.get("scoreOverall") else "",
        "smiles": p.get("scoreSmile"), "cries": p.get("scoreCry"),
        "reviews": p.get("reviewCount"), "bookmarks": p.get("bookmarkedUserCount"),
        "photos": p.get("photoCount"), "videos": len(p.get("videos") or []),
        "payment_ids": "|".join(str(i) for i in p.get("paymentIds") or []),
        "online_booking": flag(p.get("tableMapPoiId")), "booking_url": p.get("tableMapUrl") or "",
        "booking_menus": "|".join(f"{' '.join(m['title'].split())} ({m.get('priceTag') or ''})"
                                  for m in p.get("bookingMenu") or [] if m.get("title")),
        "promotions": titles(p.get("promotions"), "name"),
        "coupons": titles(p.get("coupons")), "vouchers": titles(p.get("vouchers")),
        "has_offer": flag(p.get("withOffer")), "premium_menu": flag(p.get("withPremiumMenu")),
        "queuing": flag(p.get("isQueuingEnabled")), "paid_account": flag(p.get("isPaidAccount")),
        "verified": flag(p.get("isVerifiedBadge")), "sponsored": flag(p.get("isSponsored")),
        "new_listing": flag(p.get("isNewPoi")), "virtual": flag(p.get("isVirtualPoi")),
        "award_status": p.get("awardStatus") or "",
        "door_photo": (p.get("doorPhoto") or {}).get("url") or "",
        "url": p.get("shortenUrl") or "",
        "page": f"https://www.openrice.com/en/hongkong/r-{p['latestCallName']}-r{p['poiId']}"
                if p.get("latestCallName") else "",
        "collected": today,
    }


def walk(district, pause):
    rows, start = [], 0
    while True:
        page = search(districtId=district["id"], rows=ROWS, startAt=start)["paginationResult"]
        got = page.get("results") or []
        rows += got
        start += ROWS
        if len(got) < ROWS or start >= page["count"]:
            return rows, page["count"]
        time.sleep(pause)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--district", nargs="+", help="district names as OpenRice spells them; default all")
    ap.add_argument("--list", action="store_true", help="print the districts and stop")
    ap.add_argument("--rebuild", action="store_true", help="no collecting; rebuild the CSV from the newest run")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between requests")
    args = ap.parse_args()

    todo = [] if args.rebuild else districts()
    if args.list:
        for d in todo:
            print(f"{d['count']:6}  {d['name']}")
        return
    if args.district:
        wanted = {n.lower() for n in args.district}
        unknown = wanted - {d["name"].lower() for d in todo}
        if unknown:
            raise SystemExit(f"no such district: {', '.join(sorted(unknown))} (see --list)")
        todo = [d for d in todo if d["name"].lower() in wanted]

    runs = sorted(p for p in RAW.glob("2*") if p.is_dir())
    if args.rebuild and not runs:
        raise SystemExit("nothing collected yet: run without --rebuild first")
    run = runs[-1] if args.rebuild else RAW / date.today().strftime("%Y%m%d")
    today = f"{run.name[:4]}-{run.name[4:6]}-{run.name[6:]}"
    run.mkdir(parents=True, exist_ok=True)
    for n, d in enumerate(todo, 1):
        path = run / f"{d['id']}.json.gz"
        if path.exists():
            continue
        rows, count = walk(d, args.pause)
        tmp = path.with_suffix(".part")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        tmp.rename(path)
        short = "" if len(rows) == count else f"  (OpenRice counts {count})"
        print(f"{n}/{len(todo)} {d['name']}: {len(rows)}{short}", flush=True)
        time.sleep(args.pause)

    listings = {}
    for path in sorted(run.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for p in json.load(f):
                listings.setdefault(p["poiId"], slim(p, today))
    OUT.mkdir(exist_ok=True)
    with open(OUT / "openrice_latest.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(sorted(listings.values(), key=lambda r: r["poi_id"]))
    print(f"{len(listings)} listings -> {OUT / 'openrice_latest.csv'}")


if __name__ == "__main__":
    sys.exit(main())
