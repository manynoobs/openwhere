import { useEffect, useRef } from "react";
import maplibregl, { type Map as MLMap, type MapGeoJSONFeature } from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
import { basemapStyle } from "./basemap";
import { registerBadges } from "./badges";
import { addUnitLayers, changedInFilter, setDarkTheme, setHeatMode, SRC, updateUnitLayers } from "./layers";
import { heatUrl, unitsUrl } from "../data";
import type { Filters, UnitProps } from "../types";

maplibregl.addProtocol("pmtiles", new Protocol().tile);

export interface FlyTarget {
  lon: number;
  lat: number;
  key: number; // changes on every request so the same place can be flown to twice
}

interface Props {
  year: number;
  heat: boolean;
  filters: Filters;
  heatMeta: { bounds: [number, number][]; years: number[] } | null;
  selectedId: number | null;
  focusIds: number[];
  fly: FlyTarget | null;
  pulse: number; // increments when the year bar steps, to replay the change pulse
  panelOpen: boolean;
  onSelect: (id: number | null, props?: UnitProps, at?: [number, number]) => void;
  onHover: (h: { x: number; y: number; props?: UnitProps; lngLat: [number, number] } | null) => void;
  onReady: (features: UnitProps[]) => void;
}

const HOME: [number, number] = [114.1705, 22.3082]; // Jordan / Yau Ma Tei, around Portland Street

export function MapView(p: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const ready = useRef(false);
  const latest = useRef(p);
  latest.current = p;
  const hovered = useRef<number | null>(null);
  const selected = useRef<number | null>(null);

  // create the map once
  useEffect(() => {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const map = new maplibregl.Map({
      container: el.current!,
      style: basemapStyle(dark),
      center: HOME,
      zoom: 16.1,
      minZoom: 12.5,
      maxZoom: 18.5,
      maxBounds: [
        [113.98, 22.2],
        [114.32, 22.42],
      ],
      attributionControl: { compact: window.innerWidth < 720 },
      dragRotate: false,
      pitchWithRotate: false,
      fadeDuration: 150,
    });
    map.touchZoomRotate.disableRotation();
    mapRef.current = map;
    if (import.meta.env.DEV) (window as unknown as { __map: MLMap }).__map = map;

    map.on("load", async () => {
      setDarkTheme(dark);
      registerBadges(map, dark);
      const data = await fetch(unitsUrl).then((r) => r.json());
      map.addSource(SRC, { type: "geojson", data, promoteId: "id" });
      const hm = latest.current.heatMeta;
      if (hm) addHeat(map, hm);
      addUnitLayers(map, latest.current.year, latest.current.filters);
      ready.current = true;
      latest.current.onReady(data.features.map((f: { properties: UnitProps }) => f.properties));
      sync();
    });

    const setState = (id: number | null, key: "hover" | "selected", on: boolean) => {
      if (id != null) map.setFeatureState({ source: SRC, id }, { [key]: on });
    };
    const pick = (pt: maplibregl.PointLike): MapGeoJSONFeature | undefined => {
      const layers = latest.current.heat ? ["unit-dot", "unit-badge-focus"] : ["unit-badge", "unit-dot"];
      const b: [maplibregl.PointLike, maplibregl.PointLike] = [
        [(pt as maplibregl.Point).x - 8, (pt as maplibregl.Point).y - 8],
        [(pt as maplibregl.Point).x + 8, (pt as maplibregl.Point).y + 8],
      ];
      const hits = map.queryRenderedFeatures(b, { layers: layers.filter((l) => map.getLayer(l)) });
      return hits[0];
    };

    map.on("mousemove", (e) => {
      if (!ready.current) return;
      const f = pick(e.point);
      const id = (f?.id as number | undefined) ?? null;
      if (id !== hovered.current) {
        setState(hovered.current, "hover", false);
        setState(id, "hover", true);
        hovered.current = id;
        syncFocus();
      }
      map.getCanvas().style.cursor = id != null ? "pointer" : "";
      latest.current.onHover({
        x: e.point.x,
        y: e.point.y,
        props: f?.properties as UnitProps | undefined,
        lngLat: [e.lngLat.lng, e.lngLat.lat],
      });
    });
    map.on("mouseout", () => {
      setState(hovered.current, "hover", false);
      hovered.current = null;
      syncFocus();
      latest.current.onHover(null);
    });
    map.on("click", (e) => {
      if (!ready.current) return;
      const f = pick(e.point);
      if (f) {
        const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];
        latest.current.onSelect(f.id as number, f.properties as UnitProps, coords);
      } else latest.current.onSelect(null);
    });

    function syncFocus() {
      if (!map.getLayer("unit-badge-focus")) return;
      const ids: number[] = [];
      if (latest.current.heat && hovered.current != null) ids.push(hovered.current);
      if (selected.current != null) ids.push(selected.current);
      map.setFilter("unit-badge-focus", ["in", ["get", "id"], ["literal", ids]]);
    }
    (map as unknown as { _syncFocus: () => void })._syncFocus = syncFocus;

    function sync() {
      const s = latest.current;
      updateUnitLayers(map, s.year, s.filters);
      setHeatMode(map, s.heat, s.year);
      showHeat(map, s.heat ? s.year : null, s.heatMeta?.years ?? []);
      if (selected.current !== s.selectedId) {
        setState(selected.current, "selected", false);
        setState(s.selectedId, "selected", true);
        selected.current = s.selectedId;
      }
      syncFocus();
    }
    (map as unknown as { _sync: () => void })._sync = sync;

    return () => map.remove();
  }, []);

  // keep layers in step with props
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready.current) return;
    let timer = 0;
    const run = () => {
      try {
        (map as unknown as { _sync: () => void })._sync();
      } catch {
        // the style itself is still loading: try again on the next tick
        timer = window.setTimeout(run, 60);
      }
    };
    run();
    return () => window.clearTimeout(timer);
  }, [p.year, p.heat, p.filters, p.selectedId, p.focusIds]);

  // fly to a searched or selected unit, keeping it clear of the side panel
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !p.fly) return;
    const wide = window.innerWidth > 720;
    map.flyTo({
      center: [p.fly.lon, p.fly.lat],
      zoom: Math.max(map.getZoom(), 16.6),
      padding: wide ? { right: p.panelOpen ? 420 : 0, left: 0, top: 0, bottom: 0 } : { bottom: window.innerHeight * 0.55, top: 0, left: 0, right: 0 },
      duration: 900,
      essential: true,
    });
  }, [p.fly]);

  // one ring pulse on units whose count rose in the year just shown
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready.current || p.pulse === 0) return;
    map.setFilter("unit-pulse", changedInFilter(p.year, p.filters));
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / 1100);
      const ease = 1 - Math.pow(1 - k, 3);
      map.setPaintProperty("unit-pulse", "circle-radius", 7 + ease * 16);
      map.setPaintProperty("unit-pulse", "circle-stroke-opacity", 0.9 * (1 - k));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [p.pulse]);

  return <div id="map" ref={el} role="application" aria-label="Map of licensed shopfronts" />;
}

function addHeat(map: MLMap, hm: { bounds: [number, number][]; years: number[] }) {
  const coords = hm.bounds as [[number, number], [number, number], [number, number], [number, number]];
  // the wash sits under the basemap's labels so street names stay readable
  const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
  for (const y of hm.years) {
    map.addSource(`heat-${y}`, { type: "image", url: heatUrl(y), coordinates: coords });
    map.addLayer({
      id: `heat-${y}`,
      type: "raster",
      source: `heat-${y}`,
      paint: { "raster-opacity": 0, "raster-fade-duration": 0, "raster-resampling": "linear" },
      layout: { visibility: "none" },
    }, firstLabel);
  }
}

function showHeat(map: MLMap, year: number | null, years: number[]) {
  for (const y of years) {
    const id = `heat-${y}`;
    if (!map.getLayer(id)) continue;
    const on = y === year;
    if (on) map.setLayoutProperty(id, "visibility", "visible");
    map.setPaintProperty(id, "raster-opacity", on ? 1 : 0);
    if (!on) {
      // hide after the fade so hidden layers cost nothing
      window.setTimeout(() => {
        if (map.getLayer(id) && map.getPaintProperty(id, "raster-opacity") === 0) map.setLayoutProperty(id, "visibility", "none");
      }, 500);
    }
  }
}
