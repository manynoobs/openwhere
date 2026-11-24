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

```bash
python3 fehd.py positions
```

- `latest` downloads today's lists and writes `out/fehd_latest.csv`, one row per licence.
- `history` downloads past lists from the DATA.GOV.HK historical archive: the first list of each month by default, or `--step weekly` / `--step daily`. Lists already on disk are not downloaded again. The archive goes back to January 2016, and to November 2019 for liquor.
- `positions` gives the licences a map position. The department publishes one for every restaurant, food and liquor licence in force, as point data on the government's spatial data portal; the command joins them by licence number, keeps them in `data/positions.json` and writes both CSVs again. Three requests. Positions are kept from run to run, so a licence that later lapses keeps the one it had.
- `spans` reads every list on disk and writes `out/fehd_spans.csv`: one row per licence per unbroken run with the same name, address and type. `first_seen` and `last_seen` are the first and last lists showing it; `gone_by` is the first list without it.

Every command takes `--source` to work on some of the lists, for example `--source food liquor`.

Run `latest` on a schedule (weekly is enough) and each run adds a dated list that `spans` picks up.

### Columns

`source`, `licence_no`, `type_code`, `type`, `district_code`, `district`, `name_en`, `name_tc`, `address_en`, `address_tc`, `info_codes`, `expiry`, `capacity`, `list_date`, `lat`, `lon`, `placed_by`.

- `info_codes` are FEHD's endorsement marks, such as outside seating; the legend is in each downloaded file.
- `capacity` is the head-count limit written into a liquor licence. About 750 liquor licences state one.
- The liquor list gives type and district as text, so its `type_code` and `district_code` are empty.
- `lat` and `lon` are WGS84. `placed_by` is `licence` when the position is the one the department publishes for that licence, and `address` when it is that of another licence at the same written address. On 24 Nov 2026, 42,699 of the 42,738 restaurant, food and liquor licences in force had a position of their own. The spans file has the same three columns: 111,490 of its 194,807 spans have a position.

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
- Those district files hold OpenRice's full answer for every listing, compressed (about 65 MB for a full run). The CSV is built from them, so a column can be added later without collecting again.
- The result is `out/openrice_latest.csv`, one row per listing. OpenRice files some listings under two overlapping districts (Soho and Central, for example); each is written once.
- Each run is kept under its own date, so monthly runs build a record of status changes.

### Columns

| Group | Columns |
| --- | --- |
| Identity | `poi_id`, `name_en`, `name_tc`, `category`, `url`, `page` |
| Status | `status`, `status_remark`, `moved_to_id`, `open_since`, `new_listing`, `virtual` |
| Place | `district_id`, `district`, `address_en`, `address_tc`, `floor`, `unit`, `mall`, `lat`, `lon` |
| Food and price | `price_range_id`, `price`, `cuisines`, `dishes`, `kinds`, `other_categories`, `signature_dishes` |
| Contact and hours | `phones`, `phone_remarks`, `website`, `hours` |
| Popularity | `score`, `smiles`, `cries`, `reviews`, `bookmarks`, `photos`, `videos` |
| Services | `payment_ids`, `online_booking`, `booking_url`, `booking_menus`, `queuing` |
| Offers | `promotions`, `coupons`, `vouchers`, `has_offer`, `premium_menu` |
| Account | `paid_account`, `verified`, `sponsored`, `award_status` |
| Other | `door_photo`, `collected` |

- `category` is `Beverage shop` or `Restaurant`. A beverage shop is a listing OpenRice tags as a coffee shop, Taiwanese drink shop, herbal tea shop, juice shop or tea house, whose other tags are only light food and whose name does not say restaurant, kitchen or a meal. A café that also serves meals counts as a restaurant.
- `python3 openrice.py --rebuild` writes the CSV again from the newest run on disk without collecting.
- `status` is OpenRice's own code. `10` is a listing in operation. `4` is a listing that moved; it always carries `moved_to_id`, the `poi_id` of the new listing. `3` is a listing no longer operating.
- `price` is the per-person price band. Lists such as `cuisines` and `phones` are separated by `|`.
- Yes/no columns such as `online_booking` hold `1` or nothing.
- `payment_ids` are OpenRice's own numbers for payment methods; the search results do not name them.
- `virtual` marks a listing with no dining room of its own, such as a delivery-only brand.
- A listing with a name in one language only has it in `name_en`, whatever the language.

## openrice_details.py: restaurant pages

Adds what OpenRice shows only on a restaurant's own page. Run `openrice.py` first; this reads its CSV.

```bash
python3 openrice_details.py --open-only
```

```bash
python3 openrice_details.py --district "Tsim Sha Tsui" --limit 200
```

- One page is fetched per listing and saved under `data/openrice_details/`, so a later run only fetches what is missing.
- The result is `out/openrice_details.csv`, joined to `openrice_latest.csv` on `poi_id`.
- Columns: `seats`, `description`, `price_min`, `price_max`, `facilities` (outdoor seating, service charge, corkage, Wi-Fi, parking and others), `payments` by name, `score_1` to `score_5` (OpenRice's five rating parts, in its own order), `ok_reviews`, `popular_dishes` with prices, `nearest_exit`, `hours_text`, `hours_note`, `open_late`, `landmark_ids`, `chain_listings`, `menu_photos`, `facebook`, `instagram`, `seats_booked`, `last_booking`.
- The saved page data also holds the first page of reviews and the menu photo addresses, which are not in the CSV.

OpenRice puts a security check in front of these pages when they are asked for quickly. The script stops when it meets the check and keeps what it has; run it again later to continue.

## match.py: licences joined to listings

Joins each licence to the OpenRice listing at the same premises. Run `fehd.py latest` and `openrice.py` first.

```bash
python3 match.py
```

The result is `out/matches.csv`, one row per joined licence, with `licence_no` and `poi_id` to look up either side. `basis` says how the pair was made:

| Basis | Rule |
| --- | --- |
| `name+address` | Same street and street number, and similar names |
| `name+building` | Same name and a closely matching address, for estates and malls whose licences give no street |
| `unit` | Same street number, floor and shop number as a listing in operation, whatever the names say |

A `unit` row with a low `name_score` is a licence and a listing at one shop under different names, often a new sign that one source has not caught up with. A row whose `openrice_status` is not `10` is a licence still in force for a listing OpenRice marks as moved or no longer operating.

On 22 Nov 2026:

| Licences | Joined |
| --- | --- |
| Restaurant | 12,952 of 17,254 |
| Liquor | 6,649 of 8,951 |
| Other food | 5,422 of 16,533 |
| Permit | 721 of 9,147 |

18,811 of the 28,764 OpenRice listings in operation have at least one licence joined. Most other-food licences and permits belong to supermarkets, convenience stores and kitchens that OpenRice does not list, and most permits are filed without a name.

OpenRice's terms restrict copying its content. Keep the collected files for your own analysis and do not republish them.

## Limits

- `match.py` reads addresses by rule. A licence at an address it cannot read, or under a name unlike the listing's and with no shop number, stays unjoined.
- A full monthly history of all four lists is about 1,000 files and roughly 4 GB.
- The same premises can appear in several lists under different licence numbers. Licences joined to one OpenRice listing share its `poi_id`; licences with no listing are not grouped.
- Permit type `IP` has no name in FEHD's own legend, so its `type` is empty.
- A shop that opened and closed between two downloaded lists is not seen.
- Permits have no published position, and neither has a licence that lapsed before the first `positions` run unless a later licence was written at the same address. 9,050 licences in force, nearly all permits, and 83,317 past spans are without one.
