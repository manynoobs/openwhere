import type { Map as MLMap } from "maplibre-gl";
import { dataUrl } from "../data";

// Places that draw people, from OpenStreetMap: neutral ink icons on white tiles,
// so they sit under the coloured shop pins and never compete with them.
export const PLACE_KINDS = ["mtr", "transit", "hotel", "school", "mall", "landmark", "hospital"] as const;
export type PlaceKind = (typeof PLACE_KINDS)[number];

export const PLACE_LABEL: Record<PlaceKind, string> = {
  mtr: "MTR exit",
  transit: "Station or terminus",
  hotel: "Hotel",
  school: "School or university",
  mall: "Mall or market",
  landmark: "Landmark or venue",
  hospital: "Hospital",
};

// 20 x 20 icon paths, 1.6 px strokes, drawn to match the interface icon set
export const PLACE_PATH: Record<PlaceKind, string> = {
  mtr: "M6 3.5h8a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2zM4 9.5h12M7.5 12h.01M12.5 12h.01M7 14.5l-1.5 2.5M13 14.5l1.5 2.5",
  transit: "M5 4h10a1.5 1.5 0 0 1 1.5 1.5V13a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 13V5.5A1.5 1.5 0 0 1 5 4zM3.5 10h13M6.5 14.5V16M13.5 14.5V16",
  hotel: "M3 15.5V5M3 12h14v3.5M3 9h5.5a2 2 0 0 1 2 2v1M10.5 9H15a2 2 0 0 1 2 2v1M5.8 7.8h.01",
  school: "M10 4 2.5 8 10 12l7.5-4L10 4zM5.5 9.6v3.6c1.2 1.3 2.7 2 4.5 2s3.3-.7 4.5-2V9.6M17.5 8v4.5",
  mall: "M5 7h10l-1 9.5H6L5 7zM7.5 7V6a2.5 2.5 0 0 1 5 0v1",
  landmark: "M10 3.5l1.9 4 4.3.5-3.2 3 .9 4.3L10 13.2l-3.9 2.1.9-4.3-3.2-3 4.3-.5L10 3.5z",
  hospital: "M4 4h12v12H4zM10 6.8v6.4M6.8 10h6.4",
};

const SRC = "places";

function drawIcon(kind: PlaceKind, pr: number, dark: boolean) {
  const s = 22;
  const pad = 3;
  const c = document.createElement("canvas");
  c.width = (s + pad * 2) * pr;
  c.height = (s + pad * 2 + 1) * pr;
  const g = c.getContext("2d")!;
  g.scale(pr, pr);
  g.save();
  g.shadowColor = "rgba(16, 20, 30, 0.22)";
  g.shadowBlur = 3;
  g.shadowOffsetY = 1;
  g.beginPath();
  g.roundRect(pad, pad, s, s, 6);
  g.fillStyle = dark ? "#2C2D31" : "#FFFFFF";
  g.fill();
  g.restore();
  g.translate(pad + 1, pad + 1);
  g.lineWidth = 1.6;
  g.lineCap = "round";
  g.lineJoin = "round";
  g.strokeStyle = dark ? "#E6E6EA" : "#3A3B40";
  g.stroke(new Path2D(PLACE_PATH[kind]));
  return g.getImageData(0, 0, c.width, c.height);
}

export function addPlaces(map: MLMap, dark: boolean, beforeId?: string) {
  const pr = Math.max(2, Math.ceil(window.devicePixelRatio || 1));
  for (const k of PLACE_KINDS) {
    const name = `place-${k}`;
    if (!map.hasImage(name)) map.addImage(name, drawIcon(k, pr, dark), { pixelRatio: pr });
  }
  map.addSource(SRC, { type: "geojson", data: dataUrl("facilities.geojson") });
  map.addLayer(
    {
      id: "places",
      type: "symbol",
      source: SRC,
      minzoom: 14.5,
      // MTR exits only from street zoom, where a single exit is useful
      filter: ["any", ["!=", ["get", "k"], "mtr"], [">=", ["zoom"], 16]],
      layout: {
        "icon-image": ["concat", "place-", ["get", "k"]],
        "icon-size": ["interpolate", ["linear"], ["zoom"], 14.5, 0.62, 16, 0.78, 18, 0.9],
        "icon-allow-overlap": false,
        "icon-padding": 2,
        "symbol-sort-key": ["match", ["get", "k"], "mtr", 0, "transit", 1, "mall", 2, "landmark", 3, "hotel", 4, 5],
        "text-field": ["step", ["zoom"], "", 16.6, ["coalesce", ["get", "en"], ""]],
        "text-font": ["Noto Sans Medium"],
        "text-size": 10.5,
        "text-offset": [0, 1.25],
        "text-anchor": "top",
        "text-optional": true,
        "text-max-width": 9,
        visibility: "none",
      },
      paint: {
        "icon-opacity": 0.95,
        "text-color": dark ? "#C9C9D0" : "#5A5B61",
        "text-halo-color": dark ? "#1E1F22" : "#FFFFFF",
        "text-halo-width": 1.2,
      },
    },
    beforeId,
  );
}

export function showPlaces(map: MLMap, on: boolean) {
  if (map.getLayer("places")) map.setLayoutProperty("places", "visibility", on ? "visible" : "none");
}
