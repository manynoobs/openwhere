import type { StyleSpecification } from "maplibre-gl";
import { layers, namedFlavor, type Flavor } from "@protomaps/basemaps";

// Apple Maps–like light basemap: warm pale ground, white roads, quiet labels,
// so the change colours are the only saturated thing on screen.
const LIGHT: Flavor = {
  ...namedFlavor("light"),
  background: "#F2F0EB",
  earth: "#F2F0EB",
  park_a: "#DCEBD3",
  park_b: "#D3E6C8",
  wood_a: "#DCEBD3",
  wood_b: "#D3E6C8",
  scrub_a: "#E2EDD9",
  scrub_b: "#DCE9D2",
  water: "#B9D9EE",
  buildings: "#E6E2DA",
  pedestrian: "#EEEBE5",
  pier: "#E8E5DF",
  minor_a: "#FFFFFF",
  minor_b: "#FFFFFF",
  minor_service: "#FBFAF8",
  other: "#FBFAF8",
  link: "#FFFFFF",
  major: "#FFFFFF",
  highway: "#FFE7A8",
  minor_casing: "#E3DFD7",
  major_casing_early: "#DDD8CE",
  major_casing_late: "#DDD8CE",
  highway_casing_early: "#E9C979",
  highway_casing_late: "#E9C979",
  railway: "#D5D1C9",
  roads_label_minor: "#8A8780",
  roads_label_minor_halo: "#FFFFFF",
  roads_label_major: "#6E6B65",
  roads_label_major_halo: "#FFFFFF",
  subplace_label: "#8A8780",
  subplace_label_halo: "#F2F0EB",
  city_label: "#55524C",
  city_label_halo: "#F2F0EB",
  address_label: "#A9A59D",
  address_label_halo: "#F2F0EB",
};

const DARK: Flavor = {
  ...namedFlavor("dark"),
  background: "#1E1F22",
  earth: "#1E1F22",
  park_a: "#22302A",
  park_b: "#22302A",
  wood_a: "#22302A",
  wood_b: "#22302A",
  water: "#17263A",
  buildings: "#2A2B2F",
  minor_a: "#3A3B40",
  minor_b: "#3A3B40",
  major: "#46474D",
  highway: "#5C5546",
  roads_label_minor: "#8E8F95",
  roads_label_minor_halo: "#1E1F22",
  roads_label_major: "#A3A4AA",
  roads_label_major_halo: "#1E1F22",
};

export function basemapStyle(dark: boolean): StyleSpecification {
  const flavor = dark ? DARK : LIGHT;
  const base = layers("protomaps", flavor, { lang: "en" }).filter(
    (l) => !l.id.startsWith("pois") && !l.id.includes("landcover") && l.id !== "places_country" && l.id !== "places_region",
  );
  return {
    version: 8,
    // paint changes (heat cross-fade, mode switch) ease over this duration
    transition: { duration: 450, delay: 0 },
    // built by hand: URL() would percent-encode the {fontstack} and {range} tokens
    glyphs: new URL(".", document.baseURI).href + "fonts/{fontstack}/{range}.pbf",
    sources: {
      protomaps: {
        type: "vector",
        url: "pmtiles://" + new URL("tiles/hk.pmtiles", document.baseURI).href,
        attribution:
          '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> · <a href="https://protomaps.com">Protomaps</a> · Licence records: FEHD via DATA.GOV.HK',
      },
    },
    layers: base,
  };
}
