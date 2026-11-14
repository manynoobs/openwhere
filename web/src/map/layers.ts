import type { ExpressionSpecification, FilterSpecification, Map as MLMap } from "maplibre-gl";
import { STEPS } from "../ramp";
import { YEARS, type Filters } from "../types";

export const SRC = "units";

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
  STEPS[0].fill,
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
const DOT_FADE: ExpressionSpecification = ["interpolate", ["linear"], ["zoom"], BADGE_FROM + 0.1, 1, BADGE_FROM + 0.5, 0];
const isZero = (year: number): ExpressionSpecification => ["==", changesAt(year), 0];
// shops with no change step back: smaller, so the ones that changed read first
const DOT_RADIUS = (year: number): ExpressionSpecification => [
  "interpolate", ["linear"], ["zoom"],
  12, ["case", isZero(year), 1.4, 2.6],
  14, ["case", isZero(year), 2.2, 4],
  16, ["case", isZero(year), 3.2, 5.5],
];
const badgeSize = (year: number): ExpressionSpecification => [
  "interpolate", ["linear"], ["zoom"],
  BADGE_FROM, ["case", isZero(year), 0.5, 0.78],
  17, ["case", isZero(year), 0.72, 1],
  18.5, ["case", isZero(year), 0.85, 1.12],
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
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 7, 15, 15],
      "circle-color": "rgba(10, 132, 255, 0.16)",
      "circle-stroke-color": "rgba(10, 132, 255, 0.9)",
      "circle-stroke-width": 2,
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
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "symbol-sort-key": changesAt(year),
      "icon-size": badgeSize(year),
    },
    paint: {
      "icon-opacity": ["interpolate", ["linear"], ["zoom"], BADGE_FROM, 0, BADGE_FROM + 0.5, 1],
    },
  });
  // in heat mode the badge for the hovered or selected unit stays visible
  map.addLayer({
    id: "unit-badge-focus",
    type: "symbol",
    source: SRC,
    filter: ["in", ["get", "id"], ["literal", []]],
    layout: {
      "icon-image": badgeImage(year),
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "icon-size": 1.05,
      visibility: "none",
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
  map.setLayoutProperty("unit-badge", "symbol-sort-key", changesAt(year));
  map.setLayoutProperty("unit-badge", "icon-size", badgeSize(year));
  if (map.getLayoutProperty("unit-badge", "visibility") !== "none") map.setPaintProperty("unit-dot", "circle-radius", DOT_RADIUS(year));
  map.setLayoutProperty("unit-badge-focus", "icon-image", badgeImage(year));
}

/** units whose cumulative count rose during `year` */
export function changedInFilter(year: number, f: Filters): FilterSpecification {
  if (year === YEARS[0]) return ["==", ["get", "id"], -1];
  return ["all", unitFilter(year, f), [">", changesAt(year), changesAt(year - 1)]] as FilterSpecification;
}

/** dot styling while the heat wash is on: badges step back so the wash reads */
export function setHeatMode(map: MLMap, on: boolean, year: number) {
  map.setLayoutProperty("unit-badge", "visibility", on ? "none" : "visible");
  map.setLayoutProperty("unit-badge-focus", "visibility", on ? "visible" : "none");
  map.setPaintProperty("unit-dot", "circle-opacity", on ? 0.5 : DOT_FADE);
  map.setPaintProperty("unit-dot", "circle-stroke-opacity", on ? 0.6 : DOT_FADE);
  map.setPaintProperty(
    "unit-dot",
    "circle-radius",
    on ? ["interpolate", ["linear"], ["zoom"], 12, 1.2, 16, 3] : DOT_RADIUS(year),
  );
}
