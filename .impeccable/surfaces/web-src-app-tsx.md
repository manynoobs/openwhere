---
version: 1
slug: "web-src-app-tsx"
primary_target: "web/src/App.tsx"
related_targets: []
---

# Map screen

Scope: the whole app, one full-bleed map screen. Mode: Operate.

Audience and job: food businesses of any size scanning Hong Kong districts for a site; read change frequency per unit, open a unit's sign history and records, pin up to three and compare. Judges watch it in a 3-minute demo.

## Direction contract

THESIS: A map where every licensed shopfront carries one readable number, store changes since 2016, and a switchable heat wash shows where change is frequent. Refuses the dashboard-around-a-map arrangement: no sidebars of charts, no KPI tiles; the map is the screen.
OWN-WORLD: Apple Maps played straight. Soft warm-grey light basemap with muted roads and pale water; floating translucent panels (white at ~80% with backdrop blur, 14px radius, soft single shadow); system type (SF Pro / PingFang HK); one 5-step change ramp (grey, teal, amber, orange, red) is the only saturated colour on screen.
STORY: See which streets change often within seconds; click a badge; read the sign history beside the map; pin and compare.
FIRST VIEWPORT: Full-bleed map of Yau Tsim Mong at zoom 15.5 with number badges. Top-left floating search pill (380px). Top-right segmented control Shops | Change heat plus Filters button. Bottom-centre floating year bar with play. Bottom-left compact legend. Right panel 400px slides in on select, map stays live.
FORM: category standard chosen by the user over the rolled directions (round seed: af6c27452cbfd4a2). Signature interaction: selecting a badge flies the map, lifts the badge, and slides the panel in as one motion; heat mode cross-fades the wash in while badges settle to dots.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
