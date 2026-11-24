"""Attach OpenRice price range and cuisine to shops listed now.

    python pipeline/openrice.py     # reads hk-catering-scraper/out/openrice_latest.csv,
                                    # writes data/openrice/matches.json

The listings are every OpenRice restaurant and beverage shop in Hong Kong, collected by
hk-catering-scraper; only those OpenRice marks as operating are used. They stay out of this
repository (data/openrice/ is git-ignored): OpenRice's terms restrict copying, so only the
matched price band and cuisine labels reach the app, credited to OpenRice.

An OpenRice entry is attached to one of our shops only when the two clearly describe the
same place:
  - names match closely (85+) and the points are within 150 m, or
  - the street number and street agree and the names are similar (60+), or
  - names fairly close (70+) and the points within 60 m.
Each entry and each shop is used once, best score first. Matches judged wrong by hand can be
listed in data/openrice/rejected.json.
"""
import csv
import json
import math
import re
from collections import defaultdict

from rapidfuzz import fuzz

from export import DISTRICTS
from histories import core, is_placeholder
from ingest import ROOT
from units import parse

SRC = ROOT / "hk-catering-scraper" / "out" / "openrice_latest.csv"
OUT = ROOT / "data" / "openrice" / "matches.json"
OPERATING = "10"  # OpenRice status of a listing still trading

# OpenRice's own price labels -> the app's
PRICE_LABELS = {"Under $50": "0", "$51-100": "51", "$101-200": "101", "$201-400": "201", "$401-800": "401",
                "Over $800": "801"}
PRICE_BANDS = {"0": "Under $50", "51": "$51–100", "101": "$101–200", "201": "$201–400", "401": "$401–800", "801": "Over $800"}

# OpenRice cuisines -> the app's cuisine groups
GROUP = {
    "Hong Kong Style": "cha_chaan_teng",
    "Japanese": "japanese", "Korean": "korean",
    **{k: "chinese" for k in ["Guangdong", "Sichuan", "Chiu Chow", "Shanghai", "Yunnan", "Hunan", "Taiwan", "Beijing",
                             "Northeastern", "Guangxi", "Shunde", "Xinjiang", "Guizhou", "Fujian", "Jiang-Zhe", "Shandong",
                             "Hakka", "Shanxi (Jin)", "Shanxi (Shan)", "Huaiyang", "Jingchuanhu", "Village Food", "Mongolia"]},
    **{k: "se_asian" for k in ["Thai", "Vietnamese", "Singaporean", "Malaysian", "Philippines", "Indonesian", "Burmese"]},
    **{k: "south_asian" for k in ["Indian", "Nepalese", "Middle Eastern", "Turkish", "Lebanon", "Moroccan", "African"]},
    **{k: "western" for k in ["Western", "Italian", "American", "French", "Spanish", "British", "Mexican", "Australian",
                             "German", "Swiss", "Portuguese", "Argentinian", "Austrian", "Irish", "Brazilian", "Cuba",
                             "Mediterranean"]},
}
# dish types OpenRice does not record; a name that says one of these keeps it
DISH_TYPES = {"noodles", "hotpot_bbq", "cafe", "bar", "fast_food"}


def rows():
    for r in csv.DictReader(open(SRC, encoding="utf-8-sig")):
        if r["status"] != OPERATING or not r["lat"] or not r["lon"]:
            continue
        names = [n for n in (r["name_tc"], r["name_en"]) if n]
        if not names:
            continue
        yield {"name": names[0], "names": names, "address": r["address_en"], "lat": float(r["lat"]),
               "lon": float(r["lon"]), "min": PRICE_LABELS.get(r["price"]),
               "cuisines": [x for x in r["cuisines"].split("|") if x]}


def metres(a, b):
    k = math.cos(math.radians((a[1] + b[1]) / 2))
    return 6371000 * math.hypot(math.radians(b[0] - a[0]) * k, math.radians(b[1] - a[1]))


def name_core(s):
    s = re.sub(r"[（(][^)）]*[)）]", " ", s or "")  # branch names in brackets
    return core(s)


def name_score(a, signs):
    ca = name_core(a)
    best = 0
    for s in signs:
        cs = name_core(s)
        if not ca or not cs:
            continue
        sc = fuzz.ratio(ca, cs)
        if min(len(ca), len(cs)) >= 3 and (ca in cs or cs in ca):
            sc = max(sc, 90)
        best = max(best, sc)
    return best


def first_no(s):
    m = re.match(r"\d+", s or "")
    return int(m.group()) if m else None


def main():
    from cuisine import current_names
    shops = []
    for line in open(ROOT / "data" / "histories.jsonl"):
        r = json.loads(line)
        if r["dist"] not in DISTRICTS or r["lat"] is None or not r["listed_now"]:
            continue
        names = [n for n in (current_names(r) or []) if n and not is_placeholder(n)]
        if not names:
            continue
        a = parse(r["address_en"])
        shops.append({"unit_id": r["unit_id"], "xy": (r["lon"], r["lat"]), "names": names,
                      "street": a["street"], "no": first_no(a["street_no"])})
    ors = list(rows())

    # shops bucketed on a ~150 m grid, so each listing is compared only with shops nearby
    B = 0.0015
    bucket = defaultdict(list)
    for j, s in enumerate(shops):
        bucket[(int(s["xy"][0] // B), int(s["xy"][1] // B))].append(j)

    pairs = []
    for i, o in enumerate(ors):
        oa = parse(o["address"])
        ono = first_no(oa["street_no"])
        bx, by = int(o["lon"] // B), int(o["lat"] // B)
        for j in (j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in bucket.get((bx + dx, by + dy), ())):
            s = shops[j]
            d = metres((o["lon"], o["lat"]), s["xy"])
            if d > 150:
                continue
            ns = max(name_score(n, s["names"]) for n in o["names"])
            same_addr = oa["street"] and oa["street"] == s["street"] and ono is not None and ono == s["no"]
            if (ns >= 85) or (same_addr and ns >= 60) or (ns >= 70 and d <= 60):
                pairs.append((ns + (10 if same_addr else 0) - d / 30, i, j, ns, round(d), bool(same_addr)))
    rej_path = ROOT / "data" / "openrice" / "rejected.json"
    rejected = {tuple(x) for x in json.load(open(rej_path))} if rej_path.exists() else set()
    pairs = [p for p in pairs if (shops[p[2]]["names"][0], ors[p[1]]["name"]) not in rejected]
    pairs.sort(reverse=True)
    used_o, used_s, matches = set(), set(), {}
    for score, i, j, ns, d, same_addr in pairs:
        if i in used_o or j in used_s:
            continue
        used_o.add(i)
        used_s.add(j)
        o, s = ors[i], shops[j]
        matches[s["unit_id"]] = {
            "openrice_name": o["name"], "price": PRICE_BANDS.get(o["min"], None),
            "cuisines": o["cuisines"], "name_score": ns, "metres": d, "same_address": same_addr,
            "our_name": s["names"][0],
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(matches, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"{len(ors)} OpenRice listings trading, {len(shops)} shops listed now with a name; "
          f"{len(matches)} matched ({100 * len(matches) / len(shops):.0f}% of shops)")


def group_for(match, guessed):
    """The app's cuisine group: OpenRice's cuisine, unless the name says a dish type it lacks."""
    if guessed in DISH_TYPES:
        return guessed
    for c in match["cuisines"]:
        if c in GROUP:
            return GROUP[c]
    return guessed if guessed and guessed != "unknown" else "unknown"


if __name__ == "__main__":
    main()
