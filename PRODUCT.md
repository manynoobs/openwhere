# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vite + React + TypeScript + MapLibre GL JS, built as a static site that runs fully offline (local PMTiles basemap, precomputed data files). Python pipeline (DuckDB) produces the data. Confirmed by the user.

## Users

Anyone in the food business looking for a site in Hong Kong, from a single small shop to a large chain's site-selection team. They scan districts, compare candidate street-level units, and use how often a unit's shop sign has changed since 2016 as one reference point among others.

Secondary audience: hackathon judges watching a three-minute demo and reading the GitHub repository.

## Product Purpose

OpenWhere (formerly Shopfront Past Lives, 鋪位前世) puts ten years of public restaurant licence records on one map of Hong Kong. Every licensed unit shows how many times its shop sign changed since 2016, and a switchable layer shows where changes are frequent across a whole district. Clicking a unit shows its sign history and the records behind it; units can be pinned and compared on one time axis.

It also answers the site question directly: Site check shows same-cuisine competitors listed now within a chosen radius, how long new shops last around the spot, units licensed before with none listed now, the nearest MTR exit and the places nearby that draw people. Shop lifespan colours the streets by the share of new shops still listed three years after opening.

Success: in the first seconds a user can see which streets change often and which are stable, and within a minute they can check a spot for their cuisine and shortlist units with the evidence in view.

## Positioning

The counts are rebuilt from the FEHD licence lists themselves: provisional and full licences under the same sign are linked into one sign history by named rules, so a unit is not counted as changing hands every time a licence number changes. Every number can be traced to the dated records behind it.

## Operating Context

Used on a laptop while scanning a district, and projected on stage during a three-minute demo. Must run offline.

## Capabilities and Constraints

- Shows only what the licence lists record. Never says closed, failed, left, vacant, operator or tenant. Operator identity is unknown.
- Shows one number per unit: store changes since 2016. No raw licence-number counts and no raw-versus-reconstructed comparison in the interface.
- Does not generate advice, questions to ask, scores, grades or predictions.
- The shop lifespan layer and the places layer are off by default and switched on by the user.
- Cuisine is guessed from shop names and always labelled as such; rent is not shown because no reliable public per-shop source exists.
- Price ranges may come from a teammate's OpenRice data, pending; OpenRice terms restrict copying, so raw scraped data must not be committed to the public repository.
- Interface language: English. Shop signs and addresses are shown in Chinese and English side by side.

## Evidence on Hand

- FEHD restaurant licence lists (EN and TC), archived versions from 1 Jan 2016 to 13 Nov 2026 via DATA.GOV.HK, about 3,830 versions per language.
- Address Lookup Service building coordinates.
- No user testimonials, press quotes or business-outcome data exist; none may be invented.

## Product Principles

1. Say only what the records show; unknown is a real state, shown as such.
2. One number a person can read at a glance, with the evidence one click away.
3. The map is the product: scanning comes first, detail opens beside it without losing the map.
4. Calm by default; colour is reserved for change frequency.

## Accessibility & Inclusion

Change counts are always available as digits, not colour alone. Colour ramps must stay distinguishable for common colour-vision deficiencies.

## Brand Commitments

- Name: OpenWhere. Logo: a map pin whose head holds a shop awning (docs/brand), ink with a green awning.
- Visual direction: the category standard for map apps, played straight. Craft bar: Apple Maps (soft light basemap, translucent floating panels, system type, very smooth transitions). Chosen by the user over rolled directions on 14 Nov 2026.
