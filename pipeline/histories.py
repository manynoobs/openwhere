"""Link licences at each unit into sign histories, count store changes, generate questions.

    python pipeline/histories.py            # writes data/histories.jsonl

Only the named rules below create a link. With no rule firing, records stay separate.

  prov_then_full_same_sign   38/39 number, then a 22/31 number within 9 months, signs match  -> inferred
  prov_then_full_no_sign     same, but one sign is a placeholder ("No Record")              -> unresolved, linked
  prov_then_full_sign_differs same, but the signs differ                                    -> unresolved, not linked
  same_sign_new_number       different numbers, matching sign, gap under 12 months          -> inferred

A sign change under one licence number stays in the same sign history (verified).

Store changes = the number of times a sign history with a different sign took over the unit
after the first file. Placeholder-only links add no change, because the records hold no
different sign.
"""
import json
import re
from collections import defaultdict
from datetime import date

import duckdb
from rapidfuzz import fuzz

from ingest import DB, ROOT

OUT = ROOT / "data" / "histories.jsonl"
PROV, FULL = ("38", "39"), ("22", "31")
PLACEHOLDER = re.compile(r"^\(?\s*(no record( found)?|沒有記錄|没有記錄|沒有紀錄|---+|-|n/?a|nil)\s*\)?$", re.I)
GENERIC = re.compile(
    r"\b(RESTAURANTS?|REST\.?|CAFE|CAFÉ|COFFEE|SHOP|CO\.?|LTD\.?|LIMITED|COMPANY|KITCHEN|"
    r"FOOD|HK|HONG KONG|THE|AND|&|BRANCH|STORE|EXPRESS)\b|"
    r"(餐廳|茶餐廳|冰室|小館|酒家|酒樓|飯店|食堂|美食|小食|有限公司|公司|分店|店|館|屋)", re.I)
TYPE_NAME = {"RL": "General restaurant", "RR": "Light refreshment", "MR": "Marine restaurant"}
ENDORSE = {"#A": "Outside seating"}


def day(snap):
    return date(int(snap[:4]), int(snap[4:6]), int(snap[6:8]))


def months(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.4


def iso(snap):
    return day(snap).isoformat() if snap else None


def is_placeholder(sign):
    return not sign or bool(PLACEHOLDER.match(sign.strip()))


def core(sign):
    s = GENERIC.sub(" ", (sign or "").upper())
    return re.sub(r"[\W_]+", "", s)


def same_sign(a, b):
    """a, b: sets of sign strings (both languages). True if any pair matches after stripping."""
    for x in a:
        for y in b:
            if is_placeholder(x) or is_placeholder(y):
                continue
            cx, cy = core(x), core(y)
            if not cx or not cy:
                continue
            if cx == cy or (min(len(cx), len(cy)) >= 2 and (cx in cy or cy in cx)):
                return True
            if fuzz.ratio(cx, cy) >= 85:
                return True
    return False


def real_signs(signs):
    return {s for s in signs if not is_placeholder(s)}


def load(con):
    snaps = [r[0] for r in con.execute(
        "SELECT snap FROM snapshots WHERE lang='en' AND status='good' ORDER BY snap").fetchall()]
    nxt = {s: snaps[i + 1] if i + 1 < len(snaps) else None for i, s in enumerate(snaps)}
    tc = defaultdict(list)
    for licno, sign, a, b, address in con.execute(
            "SELECT licno, sign, first_snap, last_snap, address FROM spans WHERE lang='tc'").fetchall():
        tc[licno].append((a[:8], b[:8], sign, address))
    rows = con.execute("""
        SELECT s.licno, s.type, s.dist, s.sign, s.address, s.info, s.first_snap, s.last_snap,
               s.first_snap_not_matching, s.expdate_at_last, s.n_snaps, ua.unit_id
        FROM spans s JOIN unit_addresses ua USING (address)
        WHERE s.lang = 'en' ORDER BY s.licno, s.first_snap""").fetchall()
    return snaps, nxt, tc, rows


def tc_sign(tc, licno, snap):
    d = snap[:8]
    for a, b, sign, address in tc.get(licno, []):
        if a <= d <= b:
            return sign, address
    return None, None


def build_licences(rows, tc):
    """Group spans per licence; assign each licence to the unit holding most of its snapshots."""
    by_lic = defaultdict(list)
    for r in rows:
        by_lic[r[0]].append(r)
    per_unit = defaultdict(list)
    for licno, spans in by_lic.items():
        weight = defaultdict(int)
        for s in spans:
            weight[s[11]] += s[10]
        unit = max(weight, key=weight.get)
        spans.sort(key=lambda s: s[6])
        signs, gaps, types, infos, addresses, src = [], [], set(), set(), [], []
        for i, s in enumerate(spans):
            tcs, tca = tc_sign(tc, licno, s[6])
            if not signs or signs[-1]["en"] != s[3] or signs[-1]["tc"] != tcs:
                signs.append({"en": s[3], "tc": tcs, "first_seen": iso(s[6]), "last_seen": iso(s[7])})
            else:
                signs[-1]["last_seen"] = iso(s[7])
            if i and spans[i - 1][8] and spans[i - 1][8] < s[6]:
                gaps.append({"from": iso(spans[i - 1][8]), "to": iso(s[6])})
            types.add(s[1])
            infos |= set(re.findall(r"#[A-Z]", s[5] or ""))
            if s[4] not in [a["en"] for a in addresses]:
                addresses.append({"en": s[4], "tc": tca, "first_seen": iso(s[6])})
            src.append([s[6], s[7]])
        last = spans[-1]
        per_unit[unit].append({
            "licno": licno, "prefix": licno[:2], "dist": last[2],
            "first_snap": spans[0][6], "last_snap": last[7], "first_not_seen": last[8],
            "first_seen": iso(spans[0][6]), "last_seen": iso(last[7]),
            "expdate_last": last[9], "lic_types": sorted(types), "endorsements": sorted(infos),
            "info_last": sorted(set(re.findall(r"#[A-Z]", last[5] or ""))),
            "signs": signs, "gaps": gaps, "addresses": addresses, "src": src,
            "sign_set": {x for sg in signs for x in (sg["en"], sg["tc"]) if x},
        })
    return per_unit


def link(hist, lic):
    """Return (rule, status, linked) for joining licence `lic` onto history `hist`, or None."""
    prev = hist["licences"][-1]
    a, b = hist["sign_set"], lic["sign_set"]
    d_start = months(day(prev["first_snap"]), day(lic["first_snap"]))
    d_gap = months(day(prev["last_snap"]), day(lic["first_snap"]))
    if prev["prefix"] in PROV and lic["prefix"] in FULL and 0 <= d_start <= 9:
        if same_sign(a, b):
            return "prov_then_full_same_sign", "inferred", True
        if not real_signs(prev["sign_set"]) or not real_signs(b):
            return "prov_then_full_no_sign", "unresolved", True
        return "prov_then_full_sign_differs", "unresolved", False
    if d_gap < 12 and same_sign(a, b):
        return "same_sign_new_number", "inferred", True
    return None


def histories_for(lics, first_snap, latest_snap):
    lics.sort(key=lambda l: (l["first_snap"], l["licno"]))
    hists, transitions = [], []
    for lic in lics:
        best = None
        for h in reversed(hists):
            r = link(h, lic)
            if r and r[2]:
                best = (h, r)
                break
            if r and not best:
                best = (h, r)  # unresolved, not linked: remember for the transition record
        if best and best[1][2]:
            h, (rule, status, _) = best
            h["links"].append({"from": h["licences"][-1]["licno"], "to": lic["licno"],
                               "rule": rule, "status": status})
            h["licences"].append(lic)
            h["sign_set"] |= lic["sign_set"]
            continue
        h = {"licences": [lic], "links": [], "sign_set": set(lic["sign_set"])}
        if hists:
            transitions.append({"to_index": len(hists), "possible_link":
                                {"from": best[0]["licences"][-1]["licno"], "to": lic["licno"],
                                 "rule": best[1][0], "status": "unresolved"} if best else None})
        hists.append(h)

    out = []
    for i, h in enumerate(hists):
        L = h["licences"]
        last = max(L, key=lambda l: l["last_snap"])
        listed_now = last["last_snap"] == latest_snap
        signs = []
        for l in L:
            for sg in l["signs"]:
                if signs and signs[-1]["en"] == sg["en"] and signs[-1]["tc"] == sg["tc"]:
                    signs[-1]["last_seen"] = max(signs[-1]["last_seen"], sg["last_seen"])
                else:
                    signs.append(dict(sg))
        end = None
        if not listed_now:
            exp = last["expdate_last"]
            not_seen = day(last["first_not_seen"]) if last["first_not_seen"] else None
            if last["prefix"] in PROV and L[-1] is last:
                end = {"label": "no_successor_identified", "status": "unresolved"}
            elif exp and not_seen and months(not_seen, date.fromisoformat(exp)) > 2:
                end = {"label": "not_observed_before_recorded_expiry", "status": "verified",
                       "months_early": round(months(not_seen, date.fromisoformat(exp)))}
            else:
                end = {"label": "not_observed_after_recorded_expiry", "status": "verified"}
        out.append({
            "signs": signs,
            "operator_identity": "unknown",
            "lic_types": sorted({t for l in L for t in l["lic_types"]}),
            "endorsements": sorted({e for l in L for e in l["endorsements"]}),
            "first_seen": min(l["first_seen"] for l in L),
            "listed_before_2016": L[0]["first_snap"] == first_snap,
            "last_seen": last["last_seen"],
            "first_not_seen": iso(last["first_not_seen"]),
            "listed_in_latest_snapshot": listed_now,
            "licences": [{k: l[k] for k in ("licno", "first_seen", "last_seen", "expdate_last",
                                             "lic_types", "endorsements", "gaps", "addresses", "src")}
                         for l in L],
            "links": h["links"],
            "end": end,
            "_real": real_signs(h["sign_set"]),
            "_prov_count": sum(l["prefix"] in PROV for l in L),
            "_info_last": last["info_last"],
        })
    return out, transitions


def questions(unit, hs, gaps):
    q = []
    types = {t for h in hs for t in h["lic_types"]}
    if types == {"RR"}:
        q.append({"rule": "only_light_refreshment",
                  "text": "Only light refreshment licences appear here since 2016. Ask whether the "
                          "premises can meet general restaurant requirements before planning a full kitchen."})
    seat = [h for h in hs if "#A" in h["endorsements"]]
    if seat and "#A" not in hs[-1]["_info_last"]:
        q.append({"rule": "outside_seating_lapsed",
                  "text": f"Outside seating was recorded here {seat[0]['first_seen'][:4]}–{seat[-1]['last_seen'][:4]}. "
                          "Ask whether it can be approved again."})
    for g in gaps:
        if g["months"] >= 12:
            q.append({"rule": "long_unlisted_gap",
                      "text": f"No restaurant licence was observed here from {fmt(g['from'])} to {fmt(g['to'])}. "
                              "Ask the landlord how the unit was used."})
    for h in hs:
        if h["_prov_count"] >= 2:
            name = display_sign(h)
            q.append({"rule": "repeated_provisional",
                      "text": f"Under the sign {name}, {h['_prov_count']} provisional-pattern licence numbers "
                              "were recorded. Ask the agent or FEHD about the licensing history of the premises."})
        if h["end"] and h["end"]["label"] == "not_observed_before_recorded_expiry":
            q.append({"rule": "not_observed_before_expiry",
                      "text": f"The licence under {display_sign(h)} stopped appearing "
                              f"{h['end']['months_early']} months before its recorded expiry. "
                              "Ask why the previous business ended."})
    addr_changes = [l for h in hs for l in h["licences"] if len(l["addresses"]) > 1]
    if addr_changes:
        yr = addr_changes[0]["addresses"][1]["first_seen"][:4]
        q.append({"rule": "address_text_changed",
                  "text": f"The licensed address description changed in {yr}. "
                          "Confirm the exact unit and extent you are being offered."})
    if unit["resolution"] != "resolved":
        q.append({"rule": "not_resolved",
                  "text": "The records cannot separate this unit from its neighbours. "
                          "Ask the landlord for past licence numbers."})
    return q


def display_sign(h):
    for s in reversed(h["signs"]):
        if not is_placeholder(s["en"]) or (s["tc"] and not is_placeholder(s["tc"])):
            return s["tc"] if s["tc"] and not is_placeholder(s["tc"]) else s["en"]
    return "an unrecorded sign"


def fmt(iso_day):
    d = date.fromisoformat(iso_day)
    return d.strftime("%b %Y")


def main():
    con = duckdb.connect(str(DB), read_only=True)
    snaps, nxt, tc, rows = load(con)
    units = {r[0]: dict(zip(["unit_id", "building", "floors", "shops", "resolution", "lat", "lon",
                             "geocode_score", "dist"], r))
             for r in con.execute("SELECT * FROM units").fetchall()}
    con.close()
    first_snap, latest = snaps[0], snaps[-1]
    per_unit = build_licences(rows, tc)
    n = 0
    with open(OUT, "w") as f:
        for uid, lics in per_unit.items():
            u = units[uid]
            hs, trans = histories_for(lics, first_snap, latest)
            # store changes: a later history whose real sign differs from the one before
            changes = []
            for t in trans:
                h = hs[t["to_index"]]
                prev = hs[t["to_index"] - 1]
                if h["listed_before_2016"]:
                    continue
                if h["_real"] and not same_sign(prev["_real"] or {"?"}, h["_real"]):
                    changes.append({"year": int(h["first_seen"][:4]), "to": display_sign(h),
                                    "from": display_sign(prev), "first_seen": h["first_seen"],
                                    "possible_link": t["possible_link"]})
            # months with no licence observed at the unit
            spans = sorted((a, b, nxt[b]) for l in lics for a, b in l["src"])
            gaps, cover_end = [], None
            for a, b, nb in spans:
                if cover_end and cover_end[1] and cover_end[1] < a:
                    m = months(day(cover_end[1]), day(a))
                    if m >= 2:
                        gaps.append({"from": iso(cover_end[1]), "to": iso(a), "months": round(m)})
                if not cover_end or b > cover_end[0]:
                    cover_end = (b, nb)
            listed_now = any(h["listed_in_latest_snapshot"] for h in hs)
            current = next((h for h in reversed(hs) if h["listed_in_latest_snapshot"]), None)
            rec = {
                **{k: u[k] for k in ("unit_id", "resolution", "lat", "lon", "geocode_score", "dist")},
                "floors": json.loads(u["floors"]), "shops": json.loads(u["shops"]),
                "street_level": "G" in json.loads(u["floors"]),
                "address_en": lics[0]["addresses"][-1]["en"], "address_tc": lics[0]["addresses"][-1]["tc"],
                "store_changes": len(changes),
                "changes": changes,
                "change_years": [c["year"] for c in changes],
                "listed_now": listed_now,
                "previously_licensed_none_now": not listed_now,
                "current_listed_since": current["first_seen"] if current else None,
                "lic_type_now": current["lic_types"][-1] if current else None,
                "lic_types_ever": sorted({t for h in hs for t in h["lic_types"]}),
                "outside_seating_ever": any("#A" in h["endorsements"] for h in hs),
                "unlisted_gaps": gaps,
                "sign_histories": [{k: v for k, v in h.items() if not k.startswith("_")} for h in hs],
                "questions": questions(u, hs, gaps),
                "first_file": iso(first_snap), "latest_file": iso(latest),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} units written to {OUT}")


if __name__ == "__main__":
    main()
