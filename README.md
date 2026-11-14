# 鋪位前世 Shopfront Past Lives

A map of every shopfront in Yau Tsim (Tsim Sha Tsui, Jordan and Yau Ma Tei) that has held a restaurant licence since 2016, showing how many times each one changed hands.

Each shopfront on the map is a badge with one number: **store changes since 2016**. Grey means the same sign has been listed the whole time. Teal, amber, orange and red mean one, two, three, and four or more different signs took over. Switch on **Change heat** and the streets themselves take on a continuous colour, so you can see at a glance where shops turn over often and where they stay.

![Map of Yau Tsim with number badges](docs/desktop.png)

It is meant as a reference for anyone in the food business choosing a site, from a single noodle shop to a chain's site-selection team. It reports what the public licence lists show and nothing more. It does not predict whether a business will do well, and it never says why a shop left.

## What you can do with it

- **Scan a district.** Badges show the count for every unit. Zoom out and they become coloured dots.
- **See the trend.** *Change heat* (off by default) shades the streets by store changes per shop. It is smoothed over about 100 m and left blank wherever fewer than five shops are close by.
- **Play ten years.** The year bar replays 2016 to 2026. Units whose count rises that year pulse once.
- **Open a unit.** Click a badge, or search in English or Chinese (`砵蘭街100`, `Hau Fook`, a shop name). A side panel shows every sign at that address, the years each was listed, its licence type, and the licence records behind it.
- **Filter.** Street level or all floors, licence type, outside seating, previously licensed with none listed now, and minimum number of changes.
- **Compare and print.** Pin up to three units to see them on one time axis, then print a sheet that cites its source for every row.

![History panel for G/F, 100 Portland Street](docs/panel.png)

![Change heat over Tsim Sha Tsui](docs/heat.png)

## Run it

You need Node 18 or newer. All the data the app needs is already in the repository, and the app runs offline. It makes no network requests at all, not even for map tiles.

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173. For a static build, run `npm run build` and serve `web/dist` from any web server, or run `npm run preview`.

## How a store change is counted

The source is the Food and Environmental Hygiene Department's restaurant licence list, which DATA.GOV.HK has archived daily since 2016 in English and Chinese. Each row gives a licence number, a sign, an address, a licence type and an expiry date. Nothing in it names an operator or a tenant, so the app never does either.

Counting licence numbers would overstate how often shops change. A new restaurant usually gets a six-month provisional licence (numbers starting 38 or 39) and then a full licence (22 or 31), which is two numbers for one shop. So the pipeline links records into **sign histories**, using only these named rules:

| Records show | Treated as |
| --- | --- |
| Same licence number, sign text changes | One history, "sign changed under the same licence" |
| Provisional number, then a full number within 9 months, signs match in either language | One history (inferred link) |
| As above, but the first sign is a placeholder such as "No Record" | One history, marked unresolved |
| As above, but the signs differ | Two histories; flagged "signs differ, may be linked" |
| Different numbers, matching sign, gap under 12 months | One history (inferred link) |
| Anything else | Separate histories |

A **store change** is counted when a history with a different sign is listed after the previous one at that unit stopped being listed. A shop that opens beside another, without replacing it, is not a change. Addresses where two or more shops are listed at the same time for six months or more are marked as shared.

Two hand-checked examples come out as expected:

- **G/F, 100 Portland Street:** 7 licence numbers, 4 sign histories, **3 store changes** (八妹雞煲 → 聚好味 → 羊城冰室 → 喜洋洋魚湯飯專門店).
- **G/F, 11A Hau Fook Street:** 6 licence numbers, **4 store changes**. One provisional-then-full pair has different signs, so it stays unlinked and is flagged.

A licence that drops off the list for a month or two has usually just been renewed late. Of the licences that vanished from a monthly file and came back, 99.8% were back within six months, so gaps shorter than six months are never shown.

## Numbers for Yau Tsim

| | |
| --- | --- |
| Monthly files read, Jan 2016 to Nov 2026 (EN + TC) | 262, none set aside as damaged |
| Licence numbers seen in the district | 5,119 |
| Shopfronts on the map, all floors | 2,200 |
| Street-level shopfronts placed on the map | 1,121 of 1,195 (94%) |
| Street-level: no change / 1 / 2 / 3 / 4 or more | 832 / 212 / 56 / 15 / 6 |
| Street-level units with a licence before but none listed now | 268 |

Yau Tsim was picked from the 19 FEHD districts by running the same counting over all of them. It has the highest rate of store changes per street-level shop (0.34, against 0.09 to 0.28 elsewhere), the largest share of shops with at least one change (25%), and the most units with three or more changes (21, against 13 at most elsewhere). It also holds both hand-checked examples above.

## Rebuild the data

The pipeline is Python 3 with DuckDB. A full run downloads about 1.3 GB and takes around an hour, mostly spent waiting on the archive and the Address Lookup Service.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt
cd pipeline
python gate0.py probe                  # check the archive answers, EN and TC
python gate0.py pull --step monthly    # first good file of each month, EN + TC
python ingest.py                       # dated spans per licence number
python units.py parse
python units.py geocode --dist 61      # Address Lookup Service, cached
python units.py build                  # addresses -> units
python histories.py                    # link rules, store changes
python export.py                       # web/public/data
python heat.py                         # heat images per year
```

| Step | File | What it does |
| --- | --- | --- |
| Download | `pipeline/gate0.py` | Lists every archived version (the archive uses `http://` until May 2021 and `https://` after) and keeps files that pass validation. A file is quarantined if it is truncated, misses a field, repeats a licence number, or loses more than 8% of its rows. |
| Spans | `pipeline/ingest.py` | One row per licence number per unbroken run with the same sign, address, type and endorsements. Checks that the EN and TC files list the same licence numbers each day, and measures how long missing licences take to return. |
| Units | `pipeline/units.py` | Parses floor, shop numbers and street address by rule. Places buildings with the government Address Lookup Service, accepting a match only when its street name and number agree with the licence address. |
| Histories | `pipeline/histories.py` | Applies the link rules above and counts store changes. |
| Export | `pipeline/export.py`, `pipeline/heat.py` | Writes the GeoJSON, one history file per unit, a search index, and one heat image per year. |

## Repository layout

```
pipeline/         download, ingest, address resolution, link rules, export
data/             snapshots.csv (manifest of files read); raw files and caches are not committed
web/              Vite + React + TypeScript + MapLibre GL app
  public/data/    exported Yau Tsim data
  public/tiles/   Hong Kong basemap (Protomaps PMTiles extract)
  src/map/        map layers, badges, basemap style
  src/components/ search, filters, panel, compare, legend, year bar
docs/             screenshots
PRODUCT.md        product brief
```

## Limits

- Monthly sampling misses a shop that opened and closed between two monthly files.
- 74 street-level addresses (6%) could not be placed reliably and are left off the map.
- Units in one building are spread on a small ring around the building point. Where two licence addresses overlap and can't be separated, the unit shows a dashed outline and its count covers the whole address.
- Link rules can be wrong. Every link is labelled with the rule that made it, and the panel lists the licence records it rests on.
- Change heat compares areas inside this district only. Its colour scale comes from Yau Tsim's own range.

## Sources and credits

- Restaurant licence lists: Food and Environmental Hygiene Department, via the [DATA.GOV.HK historical archive](https://data.gov.hk/en/help/api-spec).
- Building locations: [Address Lookup Service](https://www.als.gov.hk), Office of the Government Chief Information Officer.
- Basemap: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, rendered with [Protomaps](https://protomaps.com) and [MapLibre GL JS](https://maplibre.org).

Reconstructed from FEHD licence lists. Not a record of ownership, tenancy or business performance.
