# hk-places-scraper

Collects shops and services in Hong Kong beyond food licences, one script per source.

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

## Limits

- OpenStreetMap is mapped by volunteers and is far from complete in Hong Kong. It holds 4,910 restaurants where the government licenses over 17,000, and 57 gyms.
- Large chains are mapped best: 7-Eleven (581), Circle K (188), Mannings (102), Starbucks (76), Watsons (57). Independent shops, beauty salons and gyms are mapped least.
- A place missing here may simply be unmapped, so the file shows where a kind of shop is known to be, not where it is absent.
