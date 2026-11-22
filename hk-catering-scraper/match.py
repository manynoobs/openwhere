"""Join government licences to OpenRice listings that describe the same premises.

    python match.py        # reads out/fehd_latest.csv and out/openrice_latest.csv,
                           # writes out/matches.csv

Neither source carries the other's id, so the join is made on address and name. A licence
and a listing are compared when they share a street and street number, read from the
Chinese address or, failing that, the English one. The pair is kept as:

  name+address   same street number, and the names are similar (0.75 or more, or 0.6
                 when the floor and shop number do not disagree)
  unit           same street number, floor and shop number as a listing in operation,
                 whatever the names say; this is the only way to place a licence filed
                 under "No Record"
  name+building  no street number in common, but the same name and a closely matching
                 address (estates and malls whose licences give no street)

Best pairs are taken first. A licence joins one listing. A listing takes one restaurant,
one food and one liquor licence, and any number of permits.

A `unit` row with a low name_score is a licence and a listing at the same shop under
different names: often a new sign that one source has not caught up with.

Standard library only; Python 3.9 or newer.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
COLS = ["source", "licence_no", "poi_id", "basis", "name_score", "licence_type",
        "licence_name_en", "licence_name_tc", "openrice_name_en", "openrice_name_tc",
        "openrice_status", "licence_address", "openrice_address"]

NO_NAME = re.compile(r"no record|沒有記錄|^void\.?$|^n\.?a\.?$", re.I)
BRACKETS = re.compile(r"[（(][^)）]*[)）]")
GENERIC = re.compile(r"restaurant|kitchen|limited|\bltd\b|company|有限公司|餐廳|酒家|海鮮|廚房")
NOT_WORD = re.compile(r"[^0-9a-z一-鿿]")
CJK = re.compile(r"[一-鿿]")

NUM = r"\d+[A-Z]?"
TC_STREET = re.compile(
    rf"([一-鿿]{{1,10}}?(?:大道|道|街|路|里|坊|巷|徑|臺|台|圍)[東南西北中]?)\s*"
    rf"({NUM})(?:\s*[-–至及,、&]\s*({NUM}))*\s*號")
EN_STREET = re.compile(
    rf"({NUM})(?:\s*[-–&,]\s*({NUM}))*,?\s+((?:[A-Z']+\s+){{0,4}}?"
    r"(?:STREET|ROAD|AVENUE|LANE|TERRACE|PATH|DRIVE|SQUARE|CIRCUIT|CRESCENT|BOULEVARD|"
    r"PLACE|COURT|WAY|BAZAAR|RISE|PARADE|PROMENADE|PRAYA|WALK|ST|RD|AVE)\b"
    r"(?:\s+(?:EAST|WEST|NORTH|SOUTH|CENTRAL))?)")
ABBREV = {"ST": "STREET", "RD": "ROAD", "AVE": "AVENUE"}
TC_FLOOR = re.compile(r"地下|地舖|地鋪|地庫|閣樓|(\d+)\s*樓")
EN_FLOOR = re.compile(r"\bG/F|GROUND FLOOR|BASEMENT|\bB\d?/F|\bM/F|MEZZANINE|(\d+)\s*/\s*F", re.I)
TC_SHOP = re.compile(r"([A-Z]{0,2}\d*[A-Z]?(?:\s*[-–至及,、&]\s*[A-Z]{0,2}\d*[A-Z]?)*)\s*號?\s*(?:舖|鋪|室|檔)")
EN_SHOP = re.compile(r"(?:SHOPS?|UNITS?|STALLS?|KIOSKS?|FLAT|ROOM|RM)\s*(?:NOS?\.?\s*)?"
                     r"([A-Z]{0,2}\d*[A-Z]?(?:\s*(?:[-–&,]|AND|TO)\s*[A-Z]{0,2}\d*[A-Z]?)*)", re.I)
PIECE = re.compile(r"[A-Z]{0,2}\d+[A-Z]?|[A-Z]{1,2}")


def core(name):
    s = GENERIC.sub(" ", BRACKETS.sub(" ", name or "").lower())
    return NOT_WORD.sub("", s)


def cores(*names):
    return {c for c in (core(n) for n in names if n and not NO_NAME.search(n)) if c}


def name_score(a, b):
    best = 0.0
    for x in a:
        for y in b:
            s = SequenceMatcher(None, x, y).ratio()
            short, long_ = sorted((x, y), key=len)
            if short in long_ and len(short) >= (2 if CJK.search(short) else 4):
                s = max(s, 0.9)
            best = max(best, s)
    return best


def numbers(first, last):
    """Street numbers named by '98' or '98-112' (same side of the street)."""
    a = int(re.match(r"\d+", first).group())
    b = int(re.match(r"\d+", last).group()) if last else a
    if not a < b <= a + 200:
        return {first, last} - {None}
    return {str(n) for n in range(a, b + 1, 2)} | {first, last}


def street_keys(tc, en):
    keys = set()
    for m in TC_STREET.finditer(tc or ""):
        keys |= {(m.group(1)[-3:], n) for n in numbers(m.group(2), m.group(3))}
    if not keys:
        for m in EN_STREET.finditer((en or "").upper()):
            words = [ABBREV.get(w, w) for w in m.group(3).split()]
            keys |= {(" ".join(words[-3:]), n) for n in numbers(m.group(1), m.group(2))}
    return keys


def floor(tc, en):
    m = TC_FLOOR.search(tc or "")
    if m:
        return m.group(1) or {"地下": "G", "地舖": "G", "地鋪": "G", "地庫": "B", "閣樓": "M"}[m.group()]
    m = EN_FLOOR.search(en or "")
    if m:
        return m.group(1) or m.group()[0].upper()
    return ""


def shops(tc, en):
    found = set()
    for rx, text in ((TC_SHOP, tc or ""), (EN_SHOP, (en or "").upper())):
        for m in rx.finditer(text):
            found |= set(PIECE.findall(re.sub(r"(?<=[A-Z])-(?=\d)", "", m.group(1).upper())))
        if found:
            break
    return found


def prepare(rows, kind):
    out = []
    for r in rows:
        tc, en = r["address_tc"], r["address_en"]
        out.append({
            "row": r, "names": cores(r["name_en"], r["name_tc"]),
            "keys": street_keys(tc, en), "floor": floor(tc, en), "shops": shops(tc, en),
            "address": NOT_WORD.sub("", (tc or en).lower()),
            "open": kind == "listing" and r["status"] == "10",
        })
    return out


def candidates(licences, listings):
    """Yield (score, basis, name_score, licence index, listing index)."""
    at = defaultdict(list)
    for j, o in enumerate(listings):
        for k in o["keys"]:
            at[k].append(j)
    by_name = defaultdict(list)
    for j, o in enumerate(listings):
        for n in o["names"]:
            by_name[n].append(j)

    for i, f in enumerate(licences):
        near = {j for k in f["keys"] for j in at.get(k, ())}
        for j in near:
            o = listings[j]
            ns = name_score(f["names"], o["names"])
            same_shop = bool(f["shops"] & o["shops"])
            same_floor = bool(f["floor"]) and f["floor"] == o["floor"]
            extra = 0.2 * same_shop + 0.1 * same_floor + 0.05 * o["open"]
            clash = (bool(f["shops"] and o["shops"]) and not same_shop
                     or bool(f["floor"] and o["floor"]) and not same_floor)
            if ns >= 0.75 or (ns >= 0.6 and not clash):
                yield ns + extra, "name+address", ns, i, j
            elif same_shop and same_floor and o["open"]:
                yield 0.3 + extra, "unit", ns, i, j
        for j in {j for n in f["names"] for j in by_name.get(n, ())} - near:
            o = listings[j]
            alike = SequenceMatcher(None, f["address"], o["address"]).ratio()
            if alike >= 0.6 or (f["shops"] & o["shops"] and f["floor"] == o["floor"] and alike >= 0.4):
                yield 0.5 + alike / 2 + 0.05 * o["open"], "name+building", 1.0, i, j


def main():
    with open(OUT / "fehd_latest.csv", encoding="utf-8-sig") as f:
        licences = prepare(list(csv.DictReader(f)), "licence")
    with open(OUT / "openrice_latest.csv", encoding="utf-8-sig") as f:
        listings = prepare(list(csv.DictReader(f)), "listing")

    pairs = sorted(candidates(licences, listings), key=lambda p: -p[0])
    used_licence, used_slot, rows = set(), set(), []
    for _, basis, ns, i, j in pairs:
        f, o = licences[i]["row"], listings[j]["row"]
        slot = (j, f["source"])
        if i in used_licence or (f["source"] != "permit" and slot in used_slot):
            continue
        used_licence.add(i)
        used_slot.add(slot)
        rows.append({
            "source": f["source"], "licence_no": f["licence_no"], "poi_id": o["poi_id"],
            "basis": basis, "name_score": round(ns, 2), "licence_type": f["type"] or f["type_code"],
            "licence_name_en": f["name_en"], "licence_name_tc": f["name_tc"],
            "openrice_name_en": o["name_en"], "openrice_name_tc": o["name_tc"],
            "openrice_status": o["status"],
            "licence_address": f["address_tc"] or f["address_en"],
            "openrice_address": o["address_tc"] or o["address_en"],
        })
    rows.sort(key=lambda r: (int(r["poi_id"]), r["source"], r["licence_no"]))
    with open(OUT / "matches.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    total = Counter(f["row"]["source"] for f in licences)
    joined = Counter(r["source"] for r in rows)
    for s in total:
        how = Counter(r["basis"] for r in rows if r["source"] == s)
        print(f"{s}: {joined[s]} of {total[s]} licences joined "
              f"({', '.join(f'{n} by {b}' for b, n in how.most_common())})")
    open_ids = {o["row"]["poi_id"] for o in listings if o["open"]}
    licensed = {r["poi_id"] for r in rows}
    print(f"OpenRice listings in operation with a licence: {len(open_ids & licensed)} of {len(open_ids)}")
    print(f"{len(rows)} rows -> {OUT / 'matches.csv'}")


if __name__ == "__main__":
    sys.exit(main())
