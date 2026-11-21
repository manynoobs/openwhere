# hk-catering-scraper

Collects every licensed food business in Hong Kong from public sources, one script per source.

## fehd.py: government licence lists

Reads four lists published by the Food and Environmental Hygiene Department, in English and Chinese, and joins the two languages by licence number.

| Source | What it lists | Licences on 21 Nov 2026 |
| --- | --- | --- |
| `restaurant` | General, light refreshment and marine restaurants | 17,259 |
| `food` | Food factories, bakeries, siu mei shops, fresh provision shops, factory canteens and others | 16,538 |
| `permit` | Restricted-food permits: sushi, oysters, frozen confections, milk, vending machines and others | 9,147 |
| `liquor` | Liquor and club liquor licences | 8,949 |

It needs Python 3.9 or newer and nothing else.

```bash
python3 fehd.py latest
```

```bash
python3 fehd.py history --start 2016-01-01
```

```bash
python3 fehd.py spans
```

- `latest` downloads today's lists and writes `out/fehd_latest.csv`, one row per licence.
- `history` downloads past lists from the DATA.GOV.HK historical archive: the first list of each month by default, or `--step weekly` / `--step daily`. Lists already on disk are not downloaded again. The archive goes back to January 2016, and to November 2019 for liquor.
- `spans` reads every list on disk and writes `out/fehd_spans.csv`: one row per licence per unbroken run with the same name, address and type. `first_seen` and `last_seen` are the first and last lists showing it; `gone_by` is the first list without it.

Every command takes `--source` to work on some of the lists, for example `--source food liquor`.

Run `latest` on a schedule (weekly is enough) and each run adds a dated list that `spans` picks up.

### Columns

`source`, `licence_no`, `type_code`, `type`, `district_code`, `district`, `name_en`, `name_tc`, `address_en`, `address_tc`, `info_codes`, `expiry`, `capacity`, `list_date`.

- `info_codes` are FEHD's endorsement marks, such as outside seating; the legend is in each downloaded file.
- `capacity` is the head-count limit written into a liquor licence. About 750 liquor licences state one.
- The liquor list gives type and district as text, so its `type_code` and `district_code` are empty.

## openrice.py: OpenRice listings

Collects every OpenRice listing in Hong Kong (33,051 on 21 Nov 2026) from the site's search results, one district at a time. It also needs nothing beyond Python.

```bash
python3 openrice.py
```

```bash
python3 openrice.py --district "Wan Chai" Jordan
```

```bash
python3 openrice.py --list
```

- A full run is about 350 requests and takes around an hour. Each district is saved as it completes under `data/openrice/<date>/`, so a stopped run resumes when started again on the same day.
- The result is `out/openrice_latest.csv`, one row per listing. OpenRice files some listings under two overlapping districts (Soho and Central, for example); each is written once.
- Each run is kept under its own date, so monthly runs build a record of status changes.

### Columns

`poi_id`, `name_en`, `name_tc`, `status`, `status_remark`, `moved_to_id`, `district_id`, `district`, `address_en`, `address_tc`, `floor`, `unit`, `mall`, `lat`, `lon`, `price_range_id`, `price`, `cuisines`, `dishes`, `kinds`, `other_categories`, `phones`, `website`, `open_since`, `hours`, `score`, `smiles`, `cries`, `reviews`, `bookmarks`, `photos`, `url`, `collected`.

- `status` is OpenRice's own code. `10` is a listing in operation. `4` is a listing that moved; it always carries `moved_to_id`, the `poi_id` of the new listing. `3` is a listing no longer operating.
- `price` is the per-person price band. Lists such as `cuisines` and `phones` are separated by `|`.
- A listing with a name in one language only has it in `name_en`, whatever the language.

OpenRice's terms restrict copying its content. Keep the collected files for your own analysis and do not republish them.

## Limits

- Nothing joins an OpenRice listing to its licence yet; that needs matching on name, address and position.
- A full monthly history of all four lists is about 1,000 files and roughly 4 GB.
- The same premises can appear in several lists under different licence numbers; nothing here merges them into one business yet.
- Permit type `IP` has no name in FEHD's own legend, so its `type` is empty.
- A shop that opened and closed between two downloaded lists is not seen.
