import type { ExpressionSpecification, FilterSpecification, Map as MLMap } from "maplibre-gl";
import { STEPS, zeroFill } from "../ramp";
import { MARKER_ANCHOR } from "./badges";
import { YEARS, type Filters } from "../types";

export const SRC = "units";

let dark = false;
/** set once from the map's theme before layers are added */
export const setDarkTheme = (on: boolean) => {
  dark = on;
};

const idx = (year: number) => year - YEARS[0];

/** cumulative store changes at the end of `year` */
export const changesAt = (year: number): ExpressionSpecification => [
  "to-number",
  ["slice", ["get", "c"], idx(year), idx(year) + 1],
];
const listedChar = (year: number): ExpressionSpecification => ["slice", ["get", "l"], idx(year), idx(year) + 1];

const stepColor = (year: number): ExpressionSpecification => [
  "step",
  changesAt(year),
  zeroFill(dark),
  1,
  STEPS[1].fill,
  2,
  STEPS[2].fill,
  3,
  STEPS[3].fill,
  4,
  STEPS[4].fill,
];

export function unitFilter(year: number, f: Filters): FilterSpecification {
  const all: unknown[] = ["all", ["!=", listedChar(year), "0"]];
  if (f.streetOnly) all.push(["==", ["get", "sl"], 1]);
  if (f.type === "RR") all.push(["==", ["get", "rr"], 1]);
  if (f.type === "RL") all.push(["==", ["get", "rr"], 0]);
  if (f.seat) all.push(["==", ["get", "seat"], 1]);
  if (f.prevOnly) all.push(["==", listedChar(year), "2"]);
  if (f.minChanges > 0) all.push([">=", changesAt(year), f.minChanges]);
  return all as FilterSpecification;
}

const badgeImage = (year: number): ExpressionSpecification => [
  "concat",
  "b-",
  ["to-string", changesAt(year)],
  "-",
  ["case", ["==", listedChar(year), "2"], "h", ["==", ["get", "res"], "b"], "d", "f"],
];

// below BADGE_FROM the map shows coloured dots; badges with digits fade in above it
const BADGE_FROM = 15.7;
// dots stay under the badges, so a badge hidden by a busier neighbour still shows as a coloured dot
// during a site check, shops outside the radius fade hard and other shops inside fade a little,
// so the same-cuisine competitors read first
const siteFade = (full: number): ExpressionSpecification => [
  "match",
  ["coalesce", ["feature-state", "site"], "none"],
  "out",
  full * 0.15,
  "in",
  full * 0.45,
  full,
];
const DOT_FADE = siteFade(1);
const BADGE_OPACITY: ExpressionSpecification = ["interpolate", ["linear"], ["zoom"], BADGE_FROM, 0, BADGE_FROM + 0.5, siteFade(1)];
const isZero = (year: number): ExpressionSpecification => ["==", changesAt(year), 0];
// shops with no change step back: smaller, so the ones that changed read first
const DOT_RADIUS = (year: number): ExpressionSpecification => [
  "interpolate", ["linear"], ["zoom"],
  12, ["case", isZero(year), 1.6, 2.6],
  14, ["case", isZero(year), 2.4, 4],
  15.7, ["case", isZero(year), 3.2, 5],
  16.4, ["case", isZero(year), 2.4, 3.2],
];
const badgeSize = (year: number): ExpressionSpecification => [
  "interpolate", ["linear"], ["zoom"],
  BADGE_FROM, ["case", isZero(year), 0.6, 0.78],
  17, ["case", isZero(year), 0.8, 1],
  18.5, ["case", isZero(year), 0.9, 1.12],
];

export function addUnitLayers(map: MLMap, year: number, f: Filters) {
  const filter = unitFilter(year, f);
  map.addLayer({
    id: "unit-dot",
    type: "circle",
    source: SRC,
    filter,
    paint: {
      "circle-radius": DOT_RADIUS(year),
      "circle-color": ["case", ["==", listedChar(year), "2"], "#FFFFFF", stepColor(year)],
      "circle-stroke-color": ["case", ["==", listedChar(year), "2"], stepColor(year), "rgba(255,255,255,0.9)"],
      "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10, 0.3, 14, 1.2],
      "circle-opacity": DOT_FADE,
      "circle-stroke-opacity": DOT_FADE,
    },
  });
  map.addLayer({
    id: "unit-pulse",
    type: "circle",
    source: SRC,
    filter: ["==", ["get", "id"], -1],
    paint: {
      "circle-radius": 8,
      "circle-color": "rgba(0,0,0,0)",
      "circle-stroke-color": stepColor(year),
      "circle-stroke-width": 2,
      "circle-stroke-opacity": 0,
    },
  });
  map.addLayer({
    id: "unit-halo",
    type: "circle",
    source: SRC,
    filter,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 6, 15, 12, 17, 16],
      "circle-color": "rgba(29, 29, 31, 0.10)",
      "circle-stroke-color": "rgba(29, 29, 31, 0.55)",
      "circle-stroke-width": 1.5,
      "circle-opacity": [
        "case",
        ["boolean", ["feature-state", "selected"], false],
        1,
        ["boolean", ["feature-state", "hover"], false],
        0.6,
        0,
      ],
      "circle-stroke-opacity": [
        "case",
        ["boolean", ["feature-state", "selected"], false],
        1,
        ["boolean", ["feature-state", "hover"], false],
        0.5,
        0,
      ],
    },
  });
  map.addLayer({
    id: "unit-badge",
    type: "symbol",
    source: SRC,
    filter,
    minzoom: BADGE_FROM,
    layout: {
      "icon-image": badgeImage(year),
      // badges never sit on top of each other; the unit with more changes places first
      "icon-allow-overlap": false,
      "icon-ignore-placement": false,
      "icon-padding": 0,
      "icon-anchor": MARKER_ANCHOR,
      "symbol-sort-key": ["-", 0, changesAt(year)],
      "icon-size": badgeSize(year),
    },
    paint: {
      "icon-opacity": BADGE_OPACITY,
    },
  });
  // site check: same-cuisine competitors always show their pin, above everything but the selection
  map.addLayer({
    id: "unit-badge-comp",
    type: "symbol",
    source: SRC,
    filter: ["in", ["get", "id"], ["literal", []]],
    layout: {
      "icon-image": badgeImage(year),
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "icon-anchor": MARKER_ANCHOR,
      "icon-size": ["interpolate", ["linear"], ["zoom"], 14, 0.8, 17, 1],
      "symbol-sort-key": ["-", 0, changesAt(year)],
    },
  });
  // the selected unit's badge lifts above the rest; in heat mode the hovered one shows too
  map.addLayer({
    id: "unit-badge-focus",
    type: "symbol",
    source: SRC,
    filter: ["in", ["get", "id"], ["literal", []]],
    layout: {
      "icon-image": badgeImage(year),
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "icon-anchor": MARKER_ANCHOR,
      "icon-size": 1.3,
    },
  });
}

export function updateUnitLayers(map: MLMap, year: number, f: Filters) {
  const filter = unitFilter(year, f);
  for (const id of ["unit-dot", "unit-halo", "unit-badge"]) map.setFilter(id, filter);
  map.setPaintProperty("unit-dot", "circle-color", ["case", ["==", listedChar(year), "2"], "#FFFFFF", stepColor(year)]);
  map.setPaintProperty("unit-dot", "circle-stroke-color", [
    "case",
    ["==", listedChar(year), "2"],
    stepColor(year),
    "rgba(255,255,255,0.9)",
  ]);
  map.setPaintProperty("unit-pulse", "circle-stroke-color", stepColor(year));
  map.setLayoutProperty("unit-badge", "icon-image", badgeImage(year));
  map.setLayoutProperty("unit-badge", "symbol-sort-key", ["-", 0, changesAt(year)]);
  map.setLayoutProperty("unit-badge", "icon-size", badgeSize(year));
  if (map.getLayoutProperty("unit-badge", "visibility") !== "none") map.setPaintProperty("unit-dot", "circle-radius", DOT_RADIUS(year));
  map.setLayoutProperty("unit-badge-focus", "icon-image", badgeImage(year));
  map.setLayoutProperty("unit-badge-comp", "icon-image", badgeImage(year));
}

/** units whose cumulative count rose during `year` */
export function changedInFilter(year: number, f: Filters): FilterSpecification {
  if (year === YEARS[0]) return ["==", ["get", "id"], -1];
  return ["all", unitFilter(year, f), [">", changesAt(year), changesAt(year - 1)]] as FilterSpecification;
}

/** dot styling while the heat wash is on: badges step back so the wash reads */
export function setHeatMode(map: MLMap, on: boolean, year: number) {
  // badges fade rather than vanish; the style's 450 ms transition carries the cross-fade
  map.setPaintProperty("unit-badge", "icon-opacity", on ? 0 : BADGE_OPACITY);
  map.setPaintProperty("unit-dot", "circle-opacity", on ? siteFade(0.5) : DOT_FADE);
  map.setPaintProperty("unit-dot", "circle-stroke-opacity", on ? siteFade(0.6) : DOT_FADE);
  map.setPaintProperty(
    "unit-dot",
    "circle-radius",
    on ? ["interpolate", ["linear"], ["zoom"], 12, 1.2, 16, 3] : DOT_RADIUS(year),
  );
}
