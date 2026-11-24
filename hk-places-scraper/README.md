# hk-places-scraper

Collects shops, services and their surroundings in Hong Kong from OpenStreetMap and government sources, one script per source.

## osm.py: OpenStreetMap

One request to the Overpass API returns every mapped place of the kinds below. It needs Python 3.9 or newer and nothing else.

```bash
python3 osm.py
```

The result is `out/osm_places.csv`, one row per place. On 23 Nov 2026:

| Category | OpenStreetMap tags | Places |
| --- | --- | --- |
| Restaurant | restaurant, fast food, food court | 4,910 |
| Lifestyle, snack and convenience | convenience, variety store, confectionery, gift, houseware | 1,333 |
| Beverage shop | cafe; coffee, tea, bubble tea and drinks shops | 769 |
| Pharmacy and health/beauty retail | pharmacy, chemist, cosmetics, perfumery, herbalist, supplements, health food, medical supply | 629 |
| Supermarket | supermarket | 508 |
| Beauty and personal care | beauty salon, hairdresser, massage, spa | 425 |
| Bar | bar, pub | 265 |
| Gym | fitness centre | 57 |

### Columns

`osm_id`, `category`, `kind`, `name`, `name_en`, `name_zh`, `brand`, `branches`, `house_number`, `street`, `building`, `unit`, `level`, `lat`, `lon`, `phone`, `website`, `opening_hours`, `cuisine`, `openrice_id`, `edited`, `collected`.

- `kind` is the OpenStreetMap tag that put the place in its category, such as `shop=chemist`.
- `branches` counts the places in the file sharing a brand, or a name where no brand is tagged. A chain is a brand with several branches.
- `openrice_id` is the OpenRice listing id where a mapper recorded one; it equals `poi_id` in hk-catering-scraper's OpenRice file.
- `edited` is the date the place was last changed on OpenStreetMap.

The data is © OpenStreetMap contributors under the Open Database Licence. It may be kept and republished with that credit.

## igeocom.py: Lands Department iGeoCom

One download returns the Lands Department's GeoCommunity Database (iGeoCom), every point of interest the government maps. It needs Python 3.9 or newer, built with OpenSSL 1.1.1 or newer, and nothing else.

```bash
python3 igeocom.py
```

The result is `out/igeocom_places.csv`, one row per place: 36,776 places in 18 classes and 142 types in the file of 19 Nov 2026. Every place is kept. `category` is filled where an iGeoCom type matches one of the project's categories:

| Category | iGeoCom types | Places |
| --- | --- | --- |
| Lifestyle, snack and convenience | CVS convenience store | 1,482 |
| Supermarket | SMK supermarket | 604 |
| Restaurant | CFS cooked food stall or centre, FLR floating restaurant | 94 |

The other 34,596 places describe the surroundings:

| Kind | iGeoCom types | Places |
| --- | --- | --- |
| Railway stations and entrances | RSN, MTA, LRA, HSN, HSA | 792 |
| Bus and green minibus termini | BUS, MIN | 1,400 |
| Ferry piers and terminals | FER, FET | 516 |
| Malls and department stores | MAL, ROI | 849 |
| Markets and municipal complexes | MKT, CSC | 276 |
| Schools, kindergarten to post-secondary | class SCH | 3,761 |
| Hospitals and clinics | HOS, CLI | 356 |
| Hotels and guest houses | HTL, GHS | 1,756 |
| Cinemas | TNC | 54 |
| Sports and leisure venues | class RSF | 7,964 |

### Columns

`igeocom_id`, `category`, `class`, `class_name`, `type`, `type_name`, `subcat`, `subcat_name`, `name_en`, `name_zh`, `floor_en`, `floor_zh`, `site_en`, `site_zh`, `area_en`, `area_zh`, `district_en`, `district_zh`, `region_en`, `region_zh`, `address_en`, `address_zh`, `lat`, `lon`, `easting`, `northing`, `phone`, `website`, `source`, `revised`, `data_date`, `collected`.

- `class`, `type` and `subcat` are iGeoCom's own codes; the names beside them come from its data dictionary, version 5.0.
- `lat` and `lon` are WGS84. `easting` and `northing` are the Hong Kong 1980 Grid coordinates the file gives.
- `source` says where the Lands Department took the place from, such as its topographic map or the private sector.
- `revised` is the date the Lands Department last changed the place. `data_date` is the date it wrote the file.

The download host serves its certificate without the intermediate that signed it, so the script fetches that intermediate from the address the certificate names before downloading.

The data is © the Government of the Hong Kong SAR, released on DATA.GOV.HK. It may be kept and republished, commercially or not, with the source acknowledged.

## csdi.py: government lists with positions

Departments publish their lists of licensed and public premises as point data on the Common Spatial Data Infrastructure portal (portal.csdi.gov.hk). Each list is one request and carries the position of every premises.

```bash
python3 csdi.py
```

```bash
python3 csdi.py pharmacies medicine_sellers
```

```bash
python3 csdi.py --list
```

A full run is 17 requests and takes about two minutes. Each list is written to `out/csdi_<name>.csv`. On 24 Nov 2026:

| Name | List | Department | Rows |
| --- | --- | --- | --- |
| `restaurant_licences` | Restaurant licences | FEHD | 17,240 |
| `food_licences` | Food licences other than restaurants | FEHD | 16,525 |
| `liquor_licences` | Licensed liquor premises | Liquor Licensing Board | 9,907 |
| `trade_licences` | Places of entertainment, bathhouses, swimming pools and others | FEHD | 2,031 |
| `hawker_licences` | Hawker licences | FEHD | 4,625 |
| `public_markets` | Public markets | FEHD | 102 |
| `pharmacies` | Authorized sellers of poisons (pharmacies) | Department of Health | 641 |
| `medicine_sellers` | Listed sellers of poisons (medicine shops) | Department of Health | 3,921 |
| `fitness_rooms` | Public fitness rooms | LCSD | 80 |
| `sports_centres` | Sports centres | LCSD | 106 |
| `hotels_guesthouses` | Licensed hotels and guesthouses | Home Affairs Department | 1,803 |
| `clubs` | Clubs with a certificate of compliance | Home Affairs Department | 506 |
| `karaoke` | Karaoke establishments | Home Affairs Department | 14 |
| `cinemas` | Cinemas | Culture, Sports and Tourism Bureau | 54 |
| `ha_shopping_centres` | Housing Authority shopping centres | Housing Authority | 56 |
| `schools` | Registered schools | Education Bureau | 12,118 |
| `hospitals` | Public hospitals | Hospital Authority | 44 |

- Each CSV keeps the department's own columns as given, which differ from list to list, and adds `lat`, `lon` (WGS84) and `collected`.
- In the three licence lists `SEARCH02_EN` is the licence number. `hk-catering-scraper/fehd.py positions` uses it to give the licence files their positions.
- Every row of every list has a position inside Hong Kong.

The data is © the Government of the Hong Kong SAR and may be kept and republished, commercially or not, with the source acknowledged.

## Limits

- OpenStreetMap is mapped by volunteers and is far from complete in Hong Kong. It holds 4,910 restaurants where the government licenses over 17,000, and 57 gyms.
- Large chains are mapped best: 7-Eleven (581), Circle K (188), Mannings (102), Starbucks (76), Watsons (57). Independent shops, beauty salons and gyms are mapped least.
- A place missing here may simply be unmapped, so the file shows where a kind of shop is known to be, not where it is absent.
- iGeoCom has no type for single restaurants, cafes, bars, gyms, pharmacies or beauty salons. Its Restaurant rows are 93 cooked food centres and stalls and one floating restaurant.
- Its convenience stores are 7-Eleven (1,094) and Circle K (388) only, and its supermarkets the large chains: Wellcome (283), PARKnSHOP (142), Fusion (61), Market Place (42). Other brands are absent.
- iGeoCom's bus places are termini, not every stop.
- iGeoCom places are revised one at a time: 6,638 were last revised in January 2020, so a shop listed may have closed.
- The portal has no list for beauty salons, hairdressers, massage establishments or private gyms. Its fitness rooms are the public ones run by the LCSD.
