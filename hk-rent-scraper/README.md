# hk-rent-scraper

Collects commercial rents in Hong Kong from public sources, one script per source, and links leases to the food shops that took them.

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
