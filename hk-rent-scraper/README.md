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

- `listings` writes `out/centaline_listings.csv`: every retail unit advertised for lease (3,219 on 22 Nov 2026). These are asking rents. Each run is kept under its date, so repeated runs show units coming on and off the market. `--usage Office` or `--usage Industrial` reads those instead.
- `transactions` writes `out/centaline_transactions.csv`: leases recorded as done, for shops, offices and industrial units, one month at a time. A finished month is not asked for again; the current and previous month are refreshed on every run.

Listing columns: `id`, `adv_no`, `property_no`, `building_id`, `name_en`, `name_tc`, `zone`, `district`, `street`, `floor`, `usage`, `size_sqft`, `rent`, `rent_per_sqft`, `rent_inclusive`, `sale_price`, `sale_price_per_sqft`, `suited_to`, `labels`, `mtr_station`, `walk`, `built`, `air_con`, `sole_agent`, `lat`, `lon`, `published`, `rent_published`, `collected`.

Transaction columns: `id`, `date`, `usage`, `name_en`, `name_tc`, `zone`, `district`, `floor`, `unit`, `area_sqft`, `rent`, `rent_per_sqft`, `estimated`, `source`, `address`, `building_id`, `property_no`.

- Rents are HK$ a month and `rent_per_sqft` is HK$ per square foot a month, as Centaline states them.
- `floor` is `Shop` for a street-level shop; other values are bands such as `Low Floor` or `Upstairs Shop`.
- `suited_to` lists the trades the agent says the unit suits; `Catering` is one of them.
- `estimated` marks a transaction whose rent Centaline estimated rather than recorded.
- Listings give a street but no street number, and a map position for most. Transactions give a building or street and no position; `building_id` is shared with listings in the same building.
- Agents' names and phone numbers are not kept.

Centaline's terms restrict copying its content. Keep the collected files for your own analysis and do not republish them.

## Limits

- Asking rents are what landlords advertise, not what tenants pay.
- Transactions cover the leases Centaline hears of, mostly through market news, not every lease in Hong Kong.
