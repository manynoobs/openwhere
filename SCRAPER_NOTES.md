# Scraper notes

Status of the Hong Kong data scrapers on the `hk-catering-scraper` branch, as of 24 Nov 2026. The scrapers are standalone and are not wired into the OpenWhere app. Each folder's README has the commands and columns.

## Done

### Restaurants and food licences (`hk-catering-scraper/`)

- `fehd.py`: every food-business licence in force (51,885) and ten years of licence history (194,807 spans since January 2016).
- `fehd.py positions`: the government's own map position for 42,699 of the 42,738 restaurant, food and liquor licences.
- `openrice.py`: every OpenRice listing in Hong Kong (32,947), each marked Restaurant or Beverage shop.
- `match.py`: licences joined to OpenRice listings (25,744 pairs).

### Rent (`hk-rent-scraper/`)

- `centaline.py`: 3,219 shops advertised for lease and 188,941 done leases since 2016 (39,598 retail), 88% with a map position. Each unit is tied to its earlier leases.
- `link.py`: retail leases linked to the food shop that probably took them (8,877 leases), graded strong, fair or weak.
- `rvd.py`, `gpa.py`, `ha.py`: government retail rent statistics since 1989, 79 government tenancy awards and 265 public-estate shop awards.

### Other shops and surroundings (`hk-places-scraper/`)

- `drugoffice.py`: 4,554 pharmacies and medicine shops, which include Mannings, Watsons, Sa Sa, Japan Home Centre, 7-Eleven and Circle K branches.
- `orphf.py`: 816 private hospitals, day procedure centres, clinics and nursing homes.
- `csdi.py`: 17 government lists with positions (hotels, hawkers, markets, cinemas, schools and more).
- `igeocom.py`: 36,776 government points of interest (stations, termini, malls, schools).
- `osm.py`: 8,896 shops and services from OpenStreetMap.

### Storage and sharing

- `hk-data-sync/sync.py`: pushes and pulls the collected data to a private storage bucket, apart from GitHub.
- The collected data (about 3.7 GB) is kept off GitHub. A local share folder holds four workbooks and three CSVs for the team.

## Not done

### Data

- Rent paid by a named restaurant: no source publishes it. The government's per-shop rateable values are free to search only from mid-March to the end of May; test that search when it next opens.
- Beauty salons, hair and nail salons, gyms and massage: no government list exists. The chains' own store locators are the remaining route.
- Chinese herbal medicine retailers (about 4,879): listed behind a disclaimer that has to be accepted by hand.
- Snack and variety chains (759 Store, Best Mart 360, Okashi Land): only partly visible through food permits.
- OpenRice restaurant pages (seats, price range, facilities): 18 collected; the site's security check stops a fast pull.
- Positions for permits, for clinics, and for 83,317 past licence spans.
- Sing Tao property news, the one source naming tenants with rents (perhaps 100 to 300 restaurant leases): no scraper yet.

### Setup

- The storage bucket is not created; `sync.py` has not run against a real one.
- Centaline answers only from some countries. A refresh needs a Hong Kong connection.

### OpenWhere features

- Wiring any of this data into the app.
- People-flow model.
- Lines showing distance and estimated travel time.
- Adjustable budget calculator.
