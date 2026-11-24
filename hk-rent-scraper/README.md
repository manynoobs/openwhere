# hk-rent-scraper

Collects shop rents in Hong Kong from an estate agency and from government sources, one script per source, and links leases to the food shops that took them.

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

```bash
python3 centaline.py rebuild
```

- `listings` writes `out/centaline_listings.csv`: every retail unit advertised for lease (3,219 on 22 Nov 2026). These are asking rents. Each run is kept under its date, so repeated runs show units coming on and off the market. `--usage Office` or `--usage Industrial` reads those instead.
- `transactions` writes `out/centaline_transactions.csv`: leases recorded as done, for shops, offices and industrial units, one month at a time. A finished month is not asked for again; the current and previous month are refreshed on every run.

- `geocode` gives the saved leases a map position, looking up each building or address they name with the government's Address Lookup Service, and writes the transactions CSV again. Answers are kept, so a later run only looks up new places. The first run looks up about 16,500 places and takes around six hours; on 23 Nov 2026 it placed 165,563 of 188,941 leases (88%).
- `rebuild` writes both CSVs again from the saved answers without asking Centaline for anything.

Listing columns: `id`, `adv_no`, `dept`, `property_no`, `building_id`, `name_en`, `name_tc`, `zone`, `district`, `street`, `floor`, `usage`, `size_sqft`, `rent`, `rent_per_sqft`, `rent_inclusive`, `sale_price`, `sale_price_per_sqft`, `suited_to`, `labels`, `mtr_station`, `walk`, `built`, `air_con`, `sole_agent`, `with_key`, `media`, `photo`, `lat`, `lon`, `published`, `rent_published`, `collected`, `unit_leases`, `last_lease_id`, `last_let`, `last_rent`, `last_area_sqft`, `last_name_tc`.

Transaction columns: `id`, `date`, `usage`, `name_en`, `name_tc`, `zone`, `district`, `floor`, `unit`, `area_sqft`, `rent`, `rent_per_sqft`, `estimated`, `source`, `address`, `dept`, `building_id`, `building_no`, `property_no`, `unit_leases`, `previous_date`, `previous_rent`, `previous_area_sqft`, `lat`, `lon`, `placed_by`, `placed_at`.

- Rents are HK$ a month and `rent_per_sqft` is HK$ per square foot a month, as Centaline states them.
- `floor` is `Shop` or `Ground Shop` for a street-level shop; other values are bands such as `Upstairs Shop`, `Shopping Mall` or `Basement`.
- `suited_to` lists the trades the agent says the unit suits; `Catering` is one of them.
- `estimated` marks a transaction whose rent Centaline estimated rather than recorded.
- Listings give a street but no street number, and a map position for most.
- Transactions give a building or address and no position of their own. After `geocode`, `placed_by` says how sure the position is: `address` when the street and street number matched, `building` when the building or estate name matched, `street` when only the street is known and the point is some building on it. `placed_at` is the address the lookup returned. Where several buildings share a name, the one nearest the lease's district is taken, and none if even that one is more than 2 km away.
- `dept` is the Centaline department that handles the unit: Retail, Office or Industrial. Centaline numbers units and buildings within each department, so `property_no` and `building_no` identify a unit or building only together with `dept`.
- `building_no` is Centaline's own building number on a lease. It is present on 33,159 of the 39,598 retail leases, against 17,270 for `building_id`.
- `unit_leases` counts the saved leases of the same unit. On a transaction, `previous_date`, `previous_rent` and `previous_area_sqft` are the lease of that unit before this one; 5,485 retail leases have one.
- On a listing, `last_let`, `last_rent`, `last_area_sqft` and `last_name_tc` are the latest saved lease of the advertised unit, and `last_lease_id` is its `id` in the transactions file. `last_name_tc` gives the building or street number the listing leaves out. 913 of the 3,219 listings have one. Run `listings` or `rebuild` after `transactions` to refresh them.
- `with_key` marks a unit whose key the agent holds. `media` lists what the listing page carries: `video`, `360`, `VR`. `photo` is the cover picture's address.
- Agents' names and phone numbers are not kept.

Centaline's terms restrict copying its content. Keep the collected files for your own analysis and do not republish them.

## rvd.py: Rating and Valuation Department

Reads the department's Property Market Statistics for private retail premises and its yearly summary of the Valuation List, both open data on DATA.GOV.HK.

```bash
python3 rvd.py
```

One run makes 18 requests a second apart and writes four files. On 24 Nov 2026:

| File | Holds | Rows | Covers |
| --- | --- | --- | --- |
| `out/rvd_retail_rents.csv` | Average rent and price by area | 1,613 | Years and quarters from 1989, months from 1999, to Sep 2026 |
| `out/rvd_retail_indices.csv` | Rental and price indices, 1999 = 100 | 648 | Years and quarters from 1978, months from 1993, to Sep 2026 |
| `out/rvd_yields.csv` | Market yields for retail, offices and flatted factories | 519 | Years from 1987, quarters from 1990, months from 1999 |
| `out/rvd_shop_rateable_values.csv` | Shops and their rateable value in each district | 132 | As at 1 April, 2021 to 2026 |

Rent columns: `frequency`, `period`, `area`, `rent_per_sqm`, `rent_per_sqft`, `rent_note`, `price_per_sqm`, `price_per_sqft`, `price_note`.

Index columns: `frequency`, `period`, `rent_index`, `rent_note`, `price_index`, `price_note`.

Yield columns: `frequency`, `period`, then `_yield` and `_note` for each of `retail`, `office_a`, `office_b` and `flatted_factory`.

Rateable value columns: `as_at`, `area`, `district`, `shops`, `shop_rateable_value_000`, `shop_mean_rateable_value`, `other_commercial`, `other_commercial_rateable_value_000`.

- `frequency` is `year`, `quarter` or `month`, and `period` reads `1999`, `1999-Q1` or `1999-01`.
- `area` is Hong Kong (the island), Kowloon or New Territories, and New Kowloon as well until 1998.
- Rents are HK$ per square metre of internal floor area a month and prices HK$ per square metre, as published. The per square foot columns are the same figures divided by 10.764, to sit beside Centaline's.
- Notes are the department's: `P` provisional, `Z` fewer than 20 transactions, `@` and `~` an office yield that leaves out some months.
- Rateable value is the department's estimate of a year's rent at the 1 October before. `shop_rateable_value_000` is the total for the district in HK$ thousand, and `shop_mean_rateable_value` is that total divided by the number of shops, in HK$ a year.
- Rows with an empty `district` are the totals for the area, and `Overall` is all Hong Kong.

The data is from DATA.GOV.HK and may be kept and republished, crediting the Rating and Valuation Department.

## gpa.py: Government Property Agency

Reads the agency's open list of tenancies awarded by tender for shops, car parks, vending machines and cash machines in government buildings.

```bash
python3 gpa.py
```

The result is `out/gpa_awards.csv`, one row per award: 79 on 24 Nov 2026, for tenancies starting between February 2021 and October 2023. 39 are shops, 18 car parks, 16 vending machine sites and 6 ATM sites.

Columns: `ref`, `kind`, `food`, `premises`, `premises_tc`, `district`, `tenant`, `tenant_tc`, `start`, `years`, `renewal_years`, `rent`, `turnover_pct`, `lat`, `lon`.

- `kind` is `shop`, `car park`, `vending machine` or `ATM`, read from the description of the premises.
- `food` marks a shop let to a restaurant, caterer or food retailer: 13 of the 39. The list does not say what a shop may be used for, so this is judged from the tenant's name.
- `rent` is HK$ a month, exclusive of rates. Where `turnover_pct` is filled, `rent` is the minimum and the tenant pays that share of gross takings when it comes to more.
- `years` is the length of the term and `renewal_years` the further term the tenant may renew for.
- `lat` and `lon` are WGS84, as published, to about 10 metres.

The data is from DATA.GOV.HK and may be kept and republished, crediting the Government Property Agency.

## ha.py: Housing Authority

Reads the Housing Authority's notice of premises let by tender: shops, market stalls and factory units in public housing estates, with the area of each and the monthly rent the winning tender offered.

```bash
python3 ha.py
```

The notice is one PDF covering the latest twelve months. Each run keeps it under its date and writes `out/ha_awards.csv` from every kept copy, so months that have dropped off the notice stay in the file. On 24 Nov 2026 it held 265 awards from November 2025 to October 2026: 197 shops, 40 market stalls, 26 factory units and 2 large ground-floor units.

Columns: `month`, `estate`, `unit`, `kind`, `area_sqm`, `advertising_sqm`, `rent`, `later_rent`, `premium`, `rent_per_sqm`, `rent_per_sqft`.

- `month` is the month the tender was awarded.
- `rent` is HK$ a month, for shops and stalls exclusive of rates and air-conditioning charges and for factory units inclusive of rates.
- `area_sqm` is the unit alone. Where a shop is let with an advertising light box or signboard, that area is in `advertising_sqm`.
- Where the rent steps up, `rent` is for the first three years and `later_rent` for the next three.
- `premium` is the lump sum bid in a tender decided on a premium instead of a rent.

The Housing Authority keeps the copyright and allows downloading for personal or non-commercial use. Keep the collected files for your own analysis and do not republish them.

## link.py: leases joined to food shops

Links each retail lease to the food business that probably took it. It reads the transactions file and the licence history from `hk-catering-scraper`, which must sit beside this folder with `fehd.py spans` already run.

```bash
python3 link.py
```

A food business needs a licence for its premises, and the licence first appears a few months after the lease is signed: new licences in a lease's building cluster 2 to 8 months after the lease date. The result is `out/lease_links.csv`, one row per lease and shop, and `kind` says how the pair was made:

| Kind | Rule |
| --- | --- |
| `opening` | The shop's first licence at the lease's building appears 2 to 8 months after the lease, on a floor that agrees with it |
| `renewal` | The lease gives a shop number, and a shop licensed at that number was already trading and went on for at least six months |

`confidence` grades each link. Beside each count the script prints how many links the same rule makes looking 2 to 8 months before the lease instead, which is what coincidence alone produces. On 24 Nov 2026:

| Confidence | Meaning | Openings | By chance alone | Share likely real |
| --- | --- | --- | --- | --- |
| `strong` | Shop number matches, or the building has had at most 3 licensed food premises | 1,913 | 440 | about 3 in 4 |
| `fair` | 4 to 10 premises | 4,059 | 1,954 | about half |
| `weak` | 11 to 30 premises | 5,631 | 4,047 | about 3 in 10 |

There are also 305 renewals. In all 8,877 of the 39,598 retail leases are linked, and 4,580 links are to shops still licensed.

Columns: `lease_id`, `lease_date`, `building_tc`, `building_en`, `district`, `lease_floor`, `lease_unit`, `area_sqft`, `rent`, `rent_per_sqft`, `estimated`, `kind`, `months`, `basis`, `premises`, `candidates`, `confidence`, `shop_name_tc`, `shop_name_en`, `licence_nos`, `licence_types`, `licence_address`, `licensed_from`, `licensed_until`, `poi_id`, `lat`, `lon`.

- `months` is the gap from lease to first licence; it is negative for a renewal.
- `basis` is `unit` when the shop numbers match and `building` otherwise.
- `premises` counts the licensed food shops the building has had on that floor since 2016.
- `candidates` counts the shops linked to the same lease as openings. Only one of them can have taken it.
- A shop is every licence under one name at one address, so a provisional licence and the full one that replaces it are one row with both numbers in `licence_nos`.
- `licensed_until` is empty for a shop still licensed.
- `poi_id` is the shop's OpenRice listing, where `hk-catering-scraper/match.py` has joined one of its licences.

## Limits

- Neither Centaline file names a tenant. A listing is a unit on the market on the day of the run, not a shop in operation. A transaction says what a unit in a building let for on a date, not which business took it. `link.py` infers the tenant; it does not read it.
- A link is a likelihood, not a record. Buildings with more than 30 licensed food premises are left out unless the shop number matches, so leases in large malls are mostly unlinked.
- Only food businesses are linked. A lease taken by any other trade has no licence to find, and may be linked to a food shop that opened nearby by coincidence.
- A lease is linked only when its building resolves to a street number that the licence also states.
- Asking rents are what landlords advertise, not what tenants pay.
- Transactions cover the leases Centaline hears of, mostly through market news, not every lease in Hong Kong.
- Centaline answers only from some countries; from elsewhere every request gets `403 Access denied`. Hong Kong works.
- Few transactions say which unit: 2,375 of the 39,598 retail leases give a shop number. The rest give the building and a floor band, and 27,131 of them are marked as street-level shops.
- The Rating and Valuation Department publishes retail rents for three areas only, not by district, grade or street. An average moves with the mix of premises let in the period, so change over time is read from the indices.
- Rateable values are the department's estimates for every shop in a district, not rents agreed in the period, and are available by district only from 2021. The value of a single shop is in the department's Valuation List, which is free to search only from mid-March to the end of May each year.
- The Government Property Agency list has not been updated since October 2023 and gives no floor area. 25 of its 39 shops are in one building, Shun Lee Disciplined Services Quarters in Kwun Tong.
- The Housing Authority notice names neither the tenant nor the trade and gives no position. It is read from the layout of a PDF, so a change to the notice's layout would stop the script reading it.
