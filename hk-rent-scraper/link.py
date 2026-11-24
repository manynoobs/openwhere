"""Link retail leases to the food businesses that probably took them.

    python link.py         # reads out/centaline_transactions.csv and
                           # ../hk-catering-scraper/out/fehd_spans.csv, writes out/lease_links.csv

A lease names a building, not a tenant. A food business needs a licence for its premises,
and the licence first shows up a few months after the lease is signed: across all retail
leases, new licences in the same building cluster 2 to 8 months after the lease date.
A lease and a licensed shop are linked as:

  opening   the shop's first licence at the lease's building appears 2 to 8 months after
            the lease, on a floor that agrees with it
  renewal   the lease gives a shop number, and a shop licensed at that number was already
            trading and went on trading for at least six months

Licences under one name at one address (a provisional licence and the full one that
replaces it, or a restaurant and a food-factory licence) count as one shop.

`confidence` says how far to trust an opening or renewal:

  strong    the shop number matches, or the building has had at most 3 licensed food premises
  fair      4 to 10 premises
  weak      11 to 30 premises

Buildings with more than 30 are left out unless the shop number matches: in a mall that
size a new licence follows a lease no more often than chance. A pair whose shop numbers
disagree is left out too.

The run prints, beside each count, how many links the same rule makes when it looks 2 to 8
months before the lease instead, which is what coincidence alone produces.

Standard library only; Python 3.9 or newer.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
CATERING = ROOT.parent / "hk-catering-scraper"
sys.path.insert(0, str(CATERING))
from match import NOT_WORD, PIECE, core, floor, shops, street_keys  # noqa: E402

OPENS = range(2, 9)  # months from lease to first licence
STREET_LEVEL = {"Shop", "Ground Shop", "G/F", "Street", "Street Level at Shopping Mall"}
COLS = ["lease_id", "lease_date", "building_tc", "building_en", "district", "lease_floor", "lease_unit",
        "area_sqft", "rent", "rent_per_sqft", "estimated", "kind", "months", "basis", "premises",
        "candidates", "confidence", "shop_name_tc", "shop_name_en", "licence_nos", "licence_types",
        "licence_address", "licensed_from", "licensed_until", "poi_id", "lat", "lon"]


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def units(found):
    return {u.lstrip("0") or "0" for u in found}


def premises():
    """Licensed food shops: licences under one name at one address, merged."""
    spans = [r for r in read(CATERING / "out" / "fehd_spans.csv") if r["source"] in ("restaurant", "food")]
    first_list = min(r["first_seen"] for r in spans)
    found = {}
    for r in sorted(spans, key=lambda r: r["first_seen"]):
        tc, en = r["address_tc"], r["address_en"]
        key = (NOT_WORD.sub("", (tc or en).lower()), core(r["name_tc"] or r["name_en"]))
        p = found.setdefault(key, {
            "from": r["first_seen"], "until": set(), "nos": [], "types": [],
            "keys": street_keys(tc, en), "floor": floor(tc, en), "shops": units(shops(tc, en))})
        p["until"].add(r["gone_by"])
        p.update(name_tc=r["name_tc"], name_en=r["name_en"], address=tc or en)
        for field, value in (("nos", r["licence_no"]), ("types", r["type"])):
            if value and value not in p[field]:
                p[field].append(value)
    for p in found.values():
        p["until"] = "" if "" in p["until"] else max(p["until"])
        p["known_start"] = p["from"] > first_list
    return [p for p in found.values() if p["keys"]]


def lease_floor(text):
    if text in STREET_LEVEL:
        return "G"
    if text == "Basement":
        return "B"
    if text == "Upstairs Shop":
        return "up"
    m = re.fullmatch(r"(\d+)/F", text)
    return m.group(1) if m else ""


def floors_agree(lease, shop):
    if not lease or not shop:
        return True
    if lease == "up":
        return shop not in ("G", "B")
    return lease == shop


def months(a, b):
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def confidence(basis, size):
    if basis == "unit" or size <= 3:
        return "strong"
    return "fair" if size <= 10 else "weak" if size <= 30 else ""


def main():
    shops_at = defaultdict(list)
    for p in premises():
        for key in p["keys"]:
            shops_at[key].append(p)
    poi = {}
    matches = CATERING / "out" / "matches.csv"
    if matches.exists():
        poi = {r["licence_no"]: r["poi_id"] for r in read(matches)}

    leases = [r for r in read(OUT / "centaline_transactions.csv") if r["usage"] == "Retail"]
    rows, chance = [], Counter()
    for lease in leases:
        keys = street_keys(f"{lease['name_tc']} {lease['placed_at']}", "")
        level = lease_floor(lease["floor"])
        unit = units(PIECE.findall(lease["unit"].upper()))
        here = [p for p in {id(p): p for k in keys for p in shops_at.get(k, [])}.values()
                if floors_agree(level, p["floor"])]
        linked = []
        for p in here:
            same_unit = bool(unit & p["shops"])
            if unit and p["shops"] and not same_unit:
                continue
            basis = "unit" if same_unit else "building"
            level_of_trust = confidence(basis, len(here))
            gap = months(lease["date"], p["from"])
            if p["known_start"] and level_of_trust:
                if gap in OPENS:
                    linked.append(("opening", gap, basis, level_of_trust, p))
                elif -gap in OPENS:
                    chance[level_of_trust] += 1
            if same_unit and gap < 0 and (not p["until"] or months(lease["date"], p["until"]) >= 6) \
                    and not (p["known_start"] and -gap in OPENS):
                linked.append(("renewal", gap, basis, "strong", p))
        openings = sum(1 for kind, *_ in linked if kind == "opening")
        for kind, gap, basis, trust, p in linked:
            rows.append({
                "lease_id": lease["id"], "lease_date": lease["date"], "building_tc": lease["name_tc"],
                "building_en": lease["name_en"], "district": lease["district"],
                "lease_floor": lease["floor"], "lease_unit": lease["unit"],
                "area_sqft": lease["area_sqft"], "rent": lease["rent"],
                "rent_per_sqft": lease["rent_per_sqft"], "estimated": lease["estimated"],
                "kind": kind, "months": gap, "basis": basis, "premises": len(here),
                "candidates": openings if kind == "opening" else 1, "confidence": trust,
                "shop_name_tc": p["name_tc"], "shop_name_en": p["name_en"],
                "licence_nos": "|".join(p["nos"]), "licence_types": "|".join(p["types"]),
                "licence_address": p["address"], "licensed_from": p["from"],
                "licensed_until": p["until"],
                "poi_id": next((poi[n] for n in p["nos"] if n in poi), ""),
                "lat": lease["lat"], "lon": lease["lon"],
            })

    order = {"strong": 0, "fair": 1, "weak": 2}
    rows.sort(key=lambda r: (order[r["confidence"]], r["lease_date"], r["lease_id"], r["licence_nos"]))
    with open(OUT / "lease_links.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    made = Counter((r["kind"], r["confidence"]) for r in rows)
    for trust in order:
        print(f"{made['opening', trust]:6}  opening, {trust:6} ({chance[trust]} by chance alone)")
    print(f"{made['renewal', 'strong']:6}  renewal")
    print(f"{len({r['lease_id'] for r in rows})} of {len(leases)} retail leases linked, "
          f"{sum(1 for r in rows if not r['licensed_until'])} links to shops still licensed "
          f"-> {OUT / 'lease_links.csv'}")


if __name__ == "__main__":
    sys.exit(main())
