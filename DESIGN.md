---
name: OpenWhere
description: Ten years of Hong Kong restaurant licence records on one calm map, one readable change count per shopfront.
colors:
  change-0: "#3FBF6F"
  change-0-ink: "#06331A"
  change-0-dark: "#2E8C55"
  change-1: "#B4D335"
  change-1-ink: "#2C3804"
  change-2: "#FFCE3A"
  change-2-ink: "#4A3500"
  change-3: "#FF8A3A"
  change-3-ink: "#3F1500"
  change-4: "#D92D20"
  change-4-ink: "#FFFFFF"
  map-ground: "#F2F0EB"
  map-building: "#E6E2DA"
  map-park: "#DCEBD3"
  map-water: "#B9D9EE"
  map-road: "#FFFFFF"
  map-highway: "#FFE7A8"
  map-ground-dark: "#1E1F22"
  ink: "#1d1d1f"
  ink-2: "#4b4b52"
  ink-3: "#75757d"
  glass: "rgba(252, 252, 253, 0.84)"
  glass-solid: "#fcfcfd"
  fill: "rgba(118, 118, 128, 0.12)"
  fill-2: "rgba(118, 118, 128, 0.2)"
  line: "rgba(60, 60, 67, 0.14)"
  line-strong: "rgba(60, 60, 67, 0.24)"
  ink-dark: "#f2f2f5"
  glass-dark: "rgba(36, 37, 41, 0.82)"
typography:
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", \"Noto Sans HK\", \"Microsoft JhengHei\", sans-serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  figure:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1
    fontFeature: "tnum"
  year:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "17px"
    fontWeight: 600
    fontFeature: "tnum"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "15px"
    fontWeight: 600
    letterSpacing: "-0.01em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", \"Noto Sans HK\", \"Microsoft JhengHei\", sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.4
  body-small:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.4
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "12.5px"
    fontWeight: 450
    lineHeight: 1.4
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1
    fontFeature: "tnum"
  micro:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", \"PingFang HK\", sans-serif"
    fontSize: "10.5px"
    fontWeight: 400
rounded:
  tag: "6px"
  inner: "8px"
  sm: "9px"
  control: "10px"
  segmented: "11px"
  panel: "14px"
  full: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  glass-panel:
    backgroundColor: "{colors.glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.glass-solid}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  button-secondary:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "36px"
  icon-button:
    backgroundColor: "{colors.glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "0 12px"
    height: "40px"
  play-button:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.glass-solid}"
    rounded: "{rounded.full}"
    size: "36px"
  segmented:
    backgroundColor: "{colors.glass}"
    rounded: "{rounded.segmented}"
    padding: "3px"
  segmented-option:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.inner}"
    padding: "6px 16px"
  segmented-option-active:
    backgroundColor: "{colors.glass-solid}"
    textColor: "{colors.ink}"
    rounded: "{rounded.inner}"
  search-field:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "40px"
  change-chip-1:
    backgroundColor: "{colors.change-1}"
    textColor: "{colors.change-1-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: "22px"
    padding: "0 6px"
  change-chip-4:
    backgroundColor: "{colors.change-4}"
    textColor: "{colors.change-4-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: "22px"
    padding: "0 6px"
  tag:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.tag}"
    padding: "4px 8px"
  unit-panel:
    backgroundColor: "{colors.glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    width: "400px"
---

# Design System: Shopfront Past Lives

## Overview

**Creative North Star: "Apple Maps, Played Straight"**

The map is the screen. A soft, warm-grey basemap fills the viewport edge to edge, and every interface element floats above it as a translucent glass card in the system face, the way a native map app does it. Nothing is invented for its own sake: the world is the category standard for map apps, chosen by the user over rolled directions, with Apple Maps as the craft bar. Its distinctiveness comes from one thing only: a five-step change ramp (green, lime, yellow, orange, red) that is the sole saturated colour on the interface, carried by the map pins, the dots, the legend and the compare sheet. The heat wash keeps its own calmer ramp.

Density is map-app density: compact controls in the corners, a 14px body, one floating panel that slides in beside the live map rather than replacing it. Chrome is neutral ink on frosted white (or frosted graphite in dark mode); controls never borrow the ramp, so colour always means change frequency and nothing else. Motion is smooth and physical, a single long-tail ease used everywhere, with the map itself doing the largest moves (fly-to, heat cross-fade).

The build diverges from the direction contract in two small, deliberate places: the glass is 84% opaque rather than about 80%, and the top-left search is a 372px card holding the title line and a search field rather than a bare 380px pill. The build is the record.

**Key Characteristics:**
- Full-bleed vector basemap (Protomaps extract of OpenStreetMap, served offline from a local PMTiles file), tuned pale so the ramp is the only saturated thing on screen.
- Floating glass surfaces: frosted, hairline-bordered, one soft two-layer shadow, 14px corners.
- System type only (SF Pro / PingFang HK); Chinese and English set side by side.
- One five-step change ramp shared by canvas pins, map dots, pin marks in the interface and the legend; the heat images use a separate grey-to-red ramp.
- Digits always carry the count; colour is never the only cue.
- Light and dark schemes follow the operating system.

## Colors

A quiet, warm-neutral map and graphite-on-glass chrome, with one five-step ramp holding all of the saturation.

### Primary
The change ramp. Steps are 0, 1, 2, 3 and 4+ store changes since 2016; each fill has its own ink so the digit on it stays readable.
- **Steady Green** (change-0): units with no store change. Drawn smaller so changed units read first, digit kept. On the dark basemap it deepens to **Night Green** (change-0-dark).
- **Lime** (change-1) with deep olive ink: one change.
- **Signal Yellow** (change-2) with brown ink: two changes.
- **Tangerine** (change-3) with dark rust ink: three changes.
- **Alarm Red** (change-4) with white ink: four or more changes.

The heat wash is deliberately separate: pipeline/heat.py writes its own grey, teal, amber, orange, red stops into the data's metadata, and the heat legend gradient reads them from there.

### Secondary
The basemap ground, a Protomaps "light" flavour retuned toward Apple Maps.
- **Warm Paper Ground** (map-ground): land and app background; also the page colour behind the map before tiles load.
- **Stone Building** (map-building): building footprints, a half-step darker than the ground.
- **Pale Park** (map-park): parks and woods, desaturated green.
- **Pale Harbour** (map-water): water, light and low-chroma.
- **White Road** (map-road) on warm grey casings; **Soft Butter Highway** (map-highway) is the only warm accent in the basemap and stays pale.
- **Night Ground** (map-ground-dark): the dark basemap, near-black graphite with blue-black water.

### Neutral
- **Graphite Ink** (ink): primary text, the primary button, the play button, the active switch track. It is also the system's "accent": controls use ink, not colour.
- **Slate Ink** (ink-2): secondary text, inactive segment labels, addresses, English sign names under Chinese.
- **Mist Ink** (ink-3): tertiary text, placeholders, ticks, section headings in the panel, attribution links.
- **Frosted Glass** (glass) over **Glass Solid** (glass-solid): every floating surface; the solid value is the selected segment and the clear-button glyph.
- **Tint Fill / Tint Fill Strong** (fill, fill-2): search field, secondary buttons, tags, row hover, inactive switch track, compare bars.
- **Hairline / Hairline Strong** (line, line-strong): 0.5px borders and dividers on glass.
- **Dark scheme**: ink inverts to near-white (ink-dark) and glass to frosted graphite (glass-dark); every other neutral has a matching dark value in the stylesheet.

### Named Rules
**The One Colour Rule.** The change ramp is the only saturated colour on screen. Chrome is ink on glass; the basemap is pale. If a new control needs emphasis, it gets ink, weight or position, never a hue.

**The Shared Ramp Rule.** Pins, dots, pin marks and the legend read from one ramp definition. A step's colour never changes meaning between surfaces. The heat wash has its own stop list, written by the pipeline into meta.json.

**The Digit Rule.** Every coloured count also shows its number. Colour supports the digit; it never replaces it.

## Typography

**Display Font:** none; the system has no display face.
**Body Font:** system UI stack (-apple-system / SF Pro Text, Helvetica Neue, PingFang HK, Noto Sans HK, Microsoft JhengHei)
**Map Label Font:** Noto Sans glyph sets bundled with the basemap (Regular, Medium, Italic), because map labels need offline glyph files.

**Character:** Native and unadorned. Hierarchy comes from size steps of 1 to 4px and from weight (400, 450, 500, 600), never from a second family, uppercase, or tracking.

### Hierarchy
- **Figure** (600, 22px, tabular): the large change chip at the top of the unit panel; the single biggest number in the interface.
- **Headline** (600, 19px, 1.25, slightly tightened): the unit panel's address title.
- **Year** (600, 17px, tabular): the current year in the year bar.
- **Title** (600, 15–16px): app name in the top-left card, compare sheet title, popover titles; the search input sits at 15px regular.
- **Body** (400, 14px, 1.4): default text; sign names in the history step to 14.5px semibold.
- **Body Small** (400–500, 13–13.5px): addresses, filter options, toggles, About copy.
- **Caption** (450, 12.5px): secondary lines, timeline years, result subtitles, tooltips; usually Mist Ink.
- **Label** (600, 12px, line-height 1, tabular): the digits in change chips; 11–11.5px for count bubbles and the "Listed now" tag.
- **Micro** (400, 10.5px): year ticks and map attribution.

### Named Rules
**The System Face Rule.** All interface text is the platform's own UI face. No webfonts, no display face, no letter-spaced uppercase in the chrome.

**The Tabular Count Rule.** Every number that can change (counts, years, chips) uses tabular figures so it does not jitter while the year plays.

## Layout

One full-bleed map with floating corners, on a 12px outer gutter (plus safe-area insets). Top-left: the title and search card (372px). Top-right: the Shops | Change heat segmented control, the Filters button and the About button, 8px apart. Bottom-left: the compact legend (up to 332px). Bottom-centre: the year bar (up to 560px). Bottom-right: the Compare button. The unit panel docks to the right edge, 400px wide and full height minus gutters.

When the panel opens, the map stays live and everything on the right yields: top-right controls, the Compare button and the attribution slide left by the panel width plus 24px, and the year bar re-centres into the remaining space. Fly-to pads the map by 420px on the right so the selected unit lands clear of the panel.

Spacing runs on 4 / 8 / 12 / 16 / 24px. Panels pad at 16px, popovers at 16px, cards at 12px; gaps inside controls are 8px.

At 720px and below (phone), the top-right controls drop into a full-width row under the search card, the legend key line hides, the year bar sits at the bottom edge, and the unit panel becomes a bottom sheet 62% of the viewport tall. The compare sheet always rises from the bottom, spanning the width between gutters.

**The Map Stays Live Rule.** Nothing covers the map edge to edge except the compare sheet the user explicitly opens. Detail opens beside the map, and the controls move out of its way rather than under it.

## Elevation & Depth

Depth is one floating layer over the map, made by translucency, blur and a single soft shadow, Apple Maps style. Every floating card uses the same frosted treatment (22px backdrop blur with 180% saturation, 0.5px hairline border) and the same two-layer ambient shadow, deeper in dark mode. Inside a card, depth is tonal: tint fills and a raised white segment, not further shadows. On the map, badges carry their own small soft shadow and a 1.5px white keyline so they separate from the basemap and from each other.

### Shadow Vocabulary
- **Float** (`0 6px 28px rgba(15,20,30,0.14), 0 1px 3px rgba(15,20,30,0.08)`; dark `0 6px 28px rgba(0,0,0,0.45), 0 1px 3px rgba(0,0,0,0.3)`): every glass surface.
- **Raised segment** (`0 1px 4px rgba(0,0,0,0.14)`; 3px blur variant in filter segments): the selected option in a segmented control.
- **Switch knob** (`0 1px 3px rgba(0,0,0,0.25)`): the white thumb of a toggle.
- **Badge** (canvas shadow, `rgba(20,20,30,0.28)`, 3px blur, 1px down): map badges only.

### Named Rules
**The One Float Rule.** There is one elevation for chrome. Popovers, panels, tooltips, sheets and buttons all use Float; nothing stacks a second, heavier shadow.

## Shapes

Soft, continuous rounding throughout, scaled to the element: 14px for floating cards and the panel, 10–11px for fields, buttons and the segmented track, 8–9px for nested options and rows, 6px for tags, and full circles for badges, chips, the play button, the close button and switch thumbs. Borders are 0.5px hairlines; strokes inside the map are white keylines. Icons are a small authored SVG set on a 20px grid with 1.6px round-capped strokes, drawn to sit beside SF Symbols weight.

Unit markers have three forms, used consistently across map, chip and legend: **filled** (listed now), **hollow** (white centre with a ramp-coloured ring: no licence listed now), and **dashed inner ring** (shared address, located only to building level).

## Components

### Buttons
Quiet and native; ink carries emphasis.
- **Shape:** gently rounded (10px), 36px tall.
- **Primary:** Graphite Ink fill with white text, semibold, 16px side padding ("Pin to compare").
- **Secondary:** Tint Fill with ink text.
- **Icon button:** a 40px glass card (14px radius), icon plus label at weight 500, or 40px square for icon only; a small ink count bubble shows active filters.
- **Play:** a 36px ink circle with a white play or pause glyph.
- **Close:** a 30px Tint Fill circle with a Slate Ink cross.
- **Disabled:** 50% opacity. **Focus:** a 3px soft ink outline (35% ink in light, 45% in dark) offset by 1px, everywhere.

### Segmented Control
- **Style:** glass track (11px radius, 3px inset); options are text at weight 500 in Slate Ink.
- **Active:** Glass Solid pill (8px radius) with the raised-segment shadow and full ink; background, colour and shadow ease over 200ms.
- **Filter variant:** a Tint Fill track (9px) inside popovers with equal-width 13px options.

### Change Chip (signature)
The pin mark: the map pin drawn as inline SVG, reused in the legend, search results, hover card, compare rows and the panel header, so a count looks the same wherever it appears.
- **Style:** white outer pin with a soft drop shadow, ramp-filled inner pin, bold digit in the step's ink.
- **Hollow:** white inner pin with a 2px ring in the step colour (no licence listed now).
- **Sizes:** 20px in search, 22px in the legend and hover card, 26px in compare, 40px in the panel header.

### Map Badges (signature)
Drawn on canvas in the system font at 2× or higher and registered as map images, so they render like native pins without glyph files.
- Apple Maps–style pin, chosen by the user from four rendered concepts (disc, pin, ring, tile): 24px head with a 7px tail whose tip sits on the shopfront (icon-anchor bottom), white outer pin, ramp-filled inner pin with a slight top-to-bottom tonal shift, soft shadow, bold 13px digit. Zero keeps its digit and is drawn smaller.
- Below zoom 15.7 units are coloured dots (no-change dots smaller); badges fade in over half a zoom level above it and dots stay underneath.
- Badges never overlap: the unit with more changes places first, so a hidden neighbour still shows as its dot.
- Hover shows a soft ink halo at the tip; selection lifts the pin to 1.3× above all others.
- When a year step raises a unit's count, one ring pulses out from it (1.1s, ease-out cubic).

### Shop Lifespan Wash (signature)
One RGBA image generated by the data pipeline: the distance-weighted share of new shops still listed three years after opening, red (short-lived) through orange, yellow and lime to green (lasting), the pin colours read as stability. Colour fades toward white as the estimate rests on fewer shops (15 down to 3), so paleness means "less data", and nothing is drawn more than about 45 m from a shop. It sits under the basemap labels. Switching to Shop lifespan cross-fades it in over 450ms while pins fade to small dots; the legend shows the gradient with its percentage ends and "Paler colour = fewer shops to go on".

### Places
OpenStreetMap places that draw people (MTR exits, stations, hotels, schools, malls and markets, landmarks, hospitals) as 22px white tiles (6px radius, soft shadow) with ink line icons in the interface icon grammar, so they never compete with the coloured pins. Off by default behind the Places button; names appear under them from zoom 16.6; MTR exits only from zoom 16.

### Site Check
A 372px glass card under the search card. Cuisine select and a 50–500 m radius slider, then one large tabular count, the nearest six competitors as pin-mark rows with distances, a hairline-ruled list of area facts, and place counts with their icons. On the map: a dashed ink circle with a faint fill and an ink centre dot; same-cuisine competitors always show their pin on top, other shops inside the circle fade to 45% and shops outside to 15%.

### Logo
A map pin (where) whose head holds a shop awning (open): ink pin, white shopfront, green awning in the step-0 green, wordmark "Open" bold and "Where" regular in the system face. Files in docs/brand.

### Cards / Containers
- **Corner Style:** 14px.
- **Background:** Frosted Glass with blur; Float shadow; 0.5px hairline.
- **Internal Padding:** 12px (legend, search card) to 16px (panel, popovers, About).
- **Popovers:** open from their button with a 220ms scale-and-drop (from 96%, 4px up), anchored top right.

### Inputs / Fields
- **Search:** a 40px Tint Fill field (10px radius) with a Mist Ink magnifier, 15px text and Mist Ink placeholder; an 18px round clear button appears when there is text. Results list below a hairline, rows highlight with Tint Fill on hover or keyboard selection.
- **Switch:** 38 × 23px track in Tint Fill Strong, white thumb; on is ink, the thumb travels over 220ms.
- **Year slider:** the native range input in Slate Ink, with tabular year ticks every second year beneath.

### Shop Card
The 400px glass panel slides in from the right as the map flies to the shop and its pin lifts, as one motion. Built for low density, in this order: the shop listed now as a 21px headline, its cuisine (OpenRice tags, or the name-based guess marked as such), the address in English and Chinese in Mist Ink; then a hairline and a two-column fact list (12px Mist Ink labels over 16px semibold values): price per person (OpenRice band or "No data"), store changes with a 16px pin mark, how long this shop has been here, nearest MTR exit with the exit name small beneath, and a full-width kitchen line from the licence type. Actions: Check this spot (ink) and Pin to compare. Body: past shops as one line each (years column, sign name, English name small beneath, an occasional "after N months with no licence"), and the licence records, notes and source behind a disclosure.

### Compare Sheet
A bottom sheet rising over 320ms, up to 1120px wide, holding up to three pinned units as lanes on one 2016–2026 axis: a 248px identity column (pin mark, street line, floor and area), a 14px track with separated rounded bands per sign (the current one in ink), ramp-coloured dots at each store change, dashed gaps with no licence, sign names on two staggered lines under the track, and one line of facts. Empty slots show a dashed pin with an invitation to pin another.

## Do's and Don'ts

### Do:
- **Do** take every hue that means "change" on pins and controls from the five-step ramp; the heat wash keeps its own stops from meta.json.
- **Do** show the digit with every coloured count, in tabular figures.
- **Do** float new chrome as a glass card: Frosted Glass, 22px blur at 180% saturation, 0.5px hairline, Float shadow, 14px radius.
- **Do** emphasise controls with Graphite Ink (or near-white in dark mode), weight and placement.
- **Do** move with the one ease (`cubic-bezier(0.22, 1, 0.36, 1)`): 200ms for state, 220ms for popovers, 300–340ms for sheets and panels, 450ms for map paint cross-fades, 900ms for fly-to; collapse to 1ms under reduced motion.
- **Do** keep the basemap pale and low-chroma so the ramp stays the loudest thing on screen; swap the zero step to Receding Slate on the dark map.
- **Do** set Chinese and English side by side, Chinese first for sign names.
- **Do** keep map labels above the heat wash.

### Don't:
- **Don't** colour buttons, toggles, links or selection states with a ramp step or any other hue.
- **Don't** add a second typeface, a display face, or uppercase tracked labels to the interface chrome.
- **Don't** wrap the map in sidebars of charts or KPI tiles; detail opens beside the live map.
- **Don't** stack shadows or give one floating surface more elevation than another.
- **Don't** use glyph or emoji icons; extend the authored 20px SVG set at 1.6px stroke.
- **Don't** let badges overlap; resolve collisions by placing the higher count first.
