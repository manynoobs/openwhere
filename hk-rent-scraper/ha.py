"""Rents bid for Housing Authority shops and market stalls.

    python ha.py           # -> out/ha_awards.csv

The Housing Authority lets the shops, market stalls and factory units in its estates by
tender, and each month lists the premises let: the estate, the unit, its area and the
monthly rent the winning tender offered. The list is one PDF covering the latest twelve
months. Each run keeps the PDF under its date in data/ha/ and writes every award found in
the kept files, so months that have dropped off the list stay in the CSV.

`rent` is HK$ a month, for shops and stalls exclusive of rates and air-conditioning charges
and for factory units inclusive of rates. `area_sqm` is the unit alone; where a shop is let
with an advertising light box or signboard, that area is in `advertising_sqm`. Where the
rent steps up, `rent` is for the first three years and `later_rent` for the next three.
`premium` is the lump sum bid in the few tenders decided on a premium instead of a rent.

The list names neither the tenant nor the trade.

The Housing Authority keeps the copyright and allows downloading for personal or
non-commercial use. Keep the collected files for your own analysis and do not republish
them.

Standard library only; Python 3.9 or newer.
"""
import csv
import random
import re
import sys
import time
import urllib.error
import urllib.request
import zlib
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "ha"
OUT = ROOT / "out"
URL = ("https://www.housingauthority.gov.hk/en/common/pdf/commercial-properties/"
       "tender-notices-and-awards/E-Gazette.pdf")

COLS = ["month", "estate", "unit", "kind", "area_sqm", "advertising_sqm", "rent", "later_rent",
        "premium", "rent_per_sqm", "rent_per_sqft"]
COLUMNS = [(0, 187), (187, 541), (541, 640), (640, 850)]  # estate, unit, area, rent: x of each on the page
SQFT = 10.764  # square feet in a square metre
MONTH = re.compile(r"during the month of (\w+ \d{4})")
# what a page draws: a font change, a move to x y, a run of text, a filled rectangle
DRAWN = re.compile(rb"/(F\d+) [\d.]+ Tf|1 0 0 1 ([\d.]+) ([\d.]+) Tm|\[((?:\\.|[^\]\\])*)\]\s*TJ"
                   rb"|[\d.]+ ([\d.]+) ([\d.]+) ([\d.]+) re\s+f\*")


def fetch():
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "hk-rent-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} from {URL}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(5 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {URL}")


def inflate(obj):
    return zlib.decompressobj().decompress(re.search(rb"stream\r?\n(.*?)endstream", obj, re.S).group(1))


def glyphs(table):
    """Glyph number -> character, from a font's ToUnicode table."""
    numbers = lambda block: [int(h, 16) for h in re.findall(rb"<(\w+)>", block)]
    found = {}
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", table, re.S):
        n = numbers(block)
        found.update(zip(n[::2], map(chr, n[1::2])))
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", table, re.S):
        n = numbers(block)
        for first, last, char in zip(n[::3], n[1::3], n[2::3]):
            found.update((first + i, chr(char + i)) for i in range(last - first + 1))
    return found


def pages(pdf):
    """Each page as its text, [(x, y, text)], and the heights of the rules between table rows."""
    obj = {int(n): body for n, body in re.findall(rb"(\d+) 0 obj(.*?)endobj", pdf, re.S)}
    kids = next(body for body in obj.values() if b"/Kids" in body)
    for n in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids\s*\[(.*?)\]", kids, re.S).group(1)):
        page = obj[int(n)]
        fonts = {}
        for name, font in re.findall(rb"/(F\d+) (\d+) 0 R", page):
            table = re.search(rb"/ToUnicode (\d+) 0 R", obj[int(font)])
            fonts[name] = glyphs(inflate(obj[int(table.group(1))])) if table else {}
        content = inflate(obj[int(re.search(rb"/Contents (\d+) 0 R", page).group(1))])
        text, rules, glyph, at = [], set(), {}, (0, 0)
        for font, x, y, run, rule_y, width, height in DRAWN.findall(content):
            if font:
                glyph = fonts[font]
            elif x:
                at = float(x), float(y)
            elif rule_y:
                if float(width) > 300 and float(height) < 2:  # a rule under the unit column
                    rules.add(float(rule_y))
            else:
                said = ""
                for plain, coded in re.findall(rb"\(((?:\\.|[^)\\])*)\)|<(\w+)>", run):
                    if coded:
                        said += "".join(glyph[int(coded[i:i + 4], 16)] for i in range(0, len(coded), 4))
                    else:
                        said += re.sub(rb"\\(.)", rb"\1", plain).decode("latin-1")
                text.append((*at, said))
        yield text, sorted(rules, reverse=True)


def join(text):
    lines = sorted(text, key=lambda t: (-round(t[1]), t[0]))
    return " ".join("".join(said for _, _, said in lines).split())


def awards(pdf):
    month = estate = factory = premium = None
    for text, rules in pages(pdf):
        heading = MONTH.search(join(t for t in text if t[1] > rules[0]))
        if heading:
            month = datetime.strptime(heading.group(1), "%B %Y").strftime("%Y-%m")
        for top, bottom in zip(rules, rules[1:]):
            where, unit, area, paid = (join(t for t in text if bottom < t[1] < top and left <= t[0] < right)
                                       for left, right in COLUMNS)
            if unit == "Unit No.":
                factory, premium = where == "Factory", "Premium" in paid
                continue
            estate = where or estate
            area = [float(v) for v in re.findall(r"\d[\d.]*", area)]
            paid = [round(float(v.replace(",", ""))) for v in re.findall(r"\d[\d,.]*", re.sub(r"\(.*?\)", "", paid))]
            rent = "" if premium else paid[0]
            yield {"month": month, "estate": estate, "unit": unit,
                   "kind": "factory" if factory else unit.split()[0].lower(),
                   "area_sqm": area[0], "advertising_sqm": round(sum(area[1:]), 2) or "",
                   "rent": rent, "later_rent": paid[1] if len(paid) > 1 else "",
                   "premium": paid[0] if premium else "",
                   "rent_per_sqm": rent and round(rent / area[0], 1),
                   "rent_per_sqft": rent and round(rent / area[0] / SQFT, 1)}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{date.today():%Y%m%d}.pdf").write_bytes(fetch())
    found = {}
    for path in sorted(RAW.glob("*.pdf")):
        for a in awards(path.read_bytes()):
            found[a["month"], a["estate"], a["unit"]] = a
    rows = sorted(found.values(), key=lambda a: (a["month"], a["estate"], a["unit"]))
    OUT.mkdir(exist_ok=True)
    with open(OUT / "ha_awards.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    for kind, n in Counter(a["kind"] for a in rows).most_common():
        print(f"{n:6}  {kind}")
    print(f"{len(rows)} awards, {rows[0]['month']} to {rows[-1]['month']} -> {OUT / 'ha_awards.csv'}")


if __name__ == "__main__":
    sys.exit(main())
