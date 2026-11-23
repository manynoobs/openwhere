# hk-rent-scraper

Collects commercial rents in Hong Kong from public sources, one script per source.

## centaline.py: Centaline Commercial

Reads Centaline Commercial (oir.centanet.com), the commercial arm of Centaline Property.

```bash
python3 centaline.py listings
```

```bash
python3 centaline.py transactions --start 2016-01
```

```bash
python3 centaline.py geocode
```

- `listings` writes `out/centaline_listings.csv`: every retail unit advertised for lease (3,219 on 22 Nov 2026). These are asking rents. Each run is kept under its date, so repeated runs show units coming on and off the market. `--usage Office` or `--usage Industrial` reads those instead.
- `transactions` writes `out/centaline_transactions.csv`: leases recorded as done, for shops, offices and industrial units, one month at a time. A finished month is not asked for again; the current and previous month are refreshed on every run.

- `geocode` gives the saved leases a map position, looking up each building or address they name with the government's Address Lookup Service, and writes the transactions CSV again. Answers are kept, so a later run only looks up new places. The first run looks up about 16,500 places and takes around six hours; on 23 Nov 2026 it placed 165,563 of 188,941 leases (88%).

Listing columns: `id`, `adv_no`, `property_no`, `building_id`, `name_en`, `name_tc`, `zone`, `district`, `street`, `floor`, `usage`, `size_sqft`, `rent`, `rent_per_sqft`, `rent_inclusive`, `sale_price`, `sale_price_per_sqft`, `suited_to`, `labels`, `mtr_station`, `walk`, `built`, `air_con`, `sole_agent`, `lat`, `lon`, `published`, `rent_published`, `collected`.

Transaction columns: `id`, `date`, `usage`, `name_en`, `name_tc`, `zone`, `district`, `floor`, `unit`, `area_sqft`, `rent`, `rent_per_sqft`, `estimated`, `source`, `address`, `building_id`, `property_no`, `lat`, `lon`, `placed_by`, `placed_at`.

- Rents are HK$ a month and `rent_per_sqft` is HK$ per square foot a month, as Centaline states them.
- `floor` is `Shop` for a street-level shop; other values are bands such as `Low Floor` or `Upstairs Shop`.
- `suited_to` lists the trades the agent says the unit suits; `Catering` is one of them.
- `estimated` marks a transaction whose rent Centaline estimated rather than recorded.
- Listings give a street but no street number, and a map position for most.
- Transactions give a building or address and no position of their own. After `geocode`, `placed_by` says how sure the position is: `address` when the street and street number matched, `building` when the building or estate name matched, `street` when only the street is known and the point is some building on it. `placed_at` is the address the lookup returned. Where several buildings share a name, the one nearest the lease's district is taken, and none if even that one is more than 2 km away.
- Agents' names and phone numbers are not kept.

Centaline's terms restrict copying its content. Keep the collected files for your own analysis and do not republish them.

## Limits

- Asking rents are what landlords advertise, not what tenants pay.
- Transactions cover the leases Centaline hears of, mostly through market news, not every lease in Hong Kong.
