import { useEffect, useRef } from "react";
import maplibregl, { type Map as MLMap, type MapGeoJSONFeature } from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
import { basemapStyle } from "./basemap";
import { registerBadges } from "./badges";
import { addUnitLayers, changedInFilter, setDarkTheme, setHeatMode, SRC, updateUnitLayers } from "./layers";
import { heatUrl, unitsUrl } from "../data";
import { addPlaces, showPlaces } from "./places";
import { circlePolygon } from "./geo";
import { YEARS, type Filters, type HeatTile, type UnitProps } from "../types";

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
  heatMeta: { tiles: HeatTile[] } | null;
  selectedId: number | null;
  focusIds: number[];
  fly: FlyTarget | null;
  /** frame these points, e.g. every branch of a brand */
  fit: { points: [number, number][]; key: number } | null;
  pulse: number; // increments when the year bar steps, to replay the change pulse
  panelOpen: boolean;
  onSelect: (id: number | null, props?: UnitProps, at?: [number, number]) => void;
  onHover: (h: { x: number; y: number; props?: UnitProps; lngLat: [number, number] } | null) => void;
  onReady: (features: UnitProps[]) => void;
  places: boolean;
  /** a site check in progress: where, how far, and which units are competitors or inside */
  site: { lon: number; lat: number; radius: number; comp: Set<number>; inside: Set<number> } | null;
  siteMode: boolean;
  onSitePick: (lon: number, lat: number, props?: UnitProps) => void;
  onPlaceHover: (h: { x: number; y: number; name: string; kind: string } | null) => void;
}

const HOME: [number, number] = [114.1735, 22.2988]; // Tsim Sha Tsui east of Nathan Road, the densest streets

export function MapView(p: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const ready = useRef(false);
  const latest = useRef(p);
  latest.current = p;
  const hovered = useRef<number | null>(null);
  const allIds = useRef<number[]>([]);
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
        [113.82, 22.15],
        [114.45, 22.57],
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
      allIds.current = data.features.map((f: { properties: { id: number } }) => f.properties.id);
      const hm = latest.current.heatMeta;
      if (hm) addHeat(map, hm);
      addPlaces(map, dark);
      map.addSource("site", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "site-fill", type: "fill", source: "site", filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "fill-color": dark ? "#f2f2f5" : "#1d1d1f", "fill-opacity": 0.06 } });
      map.addLayer({ id: "site-line", type: "line", source: "site", filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "line-color": dark ? "#f2f2f5" : "#1d1d1f", "line-width": 1.5, "line-dasharray": [2, 2], "line-opacity": 0.7 } });
      addUnitLayers(map, latest.current.year, latest.current.filters);
      map.addLayer({ id: "site-centre", type: "circle", source: "site", filter: ["==", ["geometry-type"], "Point"],
        paint: { "circle-radius": 7, "circle-color": dark ? "#f2f2f5" : "#1d1d1f", "circle-stroke-color": "#fff", "circle-stroke-width": 3 } });
      // the compact credits control opens itself on load; start it closed
      map.getContainer().querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
      ready.current = true;
      latest.current.onReady(
        data.features.map((f: { properties: UnitProps; geometry: { coordinates: [number, number] } }) => ({
          ...f.properties,
          lon: f.geometry.coordinates[0],
          lat: f.geometry.coordinates[1],
        })),
      );
      sync();
    });

    const setState = (id: number | null, key: "hover" | "selected", on: boolean) => {
      if (id != null) map.setFeatureState({ source: SRC, id }, { [key]: on });
    };
    const pick = (pt: maplibregl.PointLike): MapGeoJSONFeature | undefined => {
      const layers = latest.current.heat
        ? ["unit-badge-comp", "unit-dot", "unit-badge-focus"]
        : ["unit-badge-comp", "unit-badge", "unit-dot"];
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
      if (!f && map.getLayer("places") && map.getLayoutProperty("places", "visibility") === "visible") {
        const pl = map.queryRenderedFeatures(e.point, { layers: ["places"] })[0];
        latest.current.onPlaceHover(pl ? { x: e.point.x, y: e.point.y, name: pl.properties.en || pl.properties.tc, kind: pl.properties.k } : null);
      } else latest.current.onPlaceHover(null);
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
      if (latest.current.siteMode) {
        latest.current.onSitePick(e.lngLat.lng, e.lngLat.lat, f?.properties as UnitProps | undefined);
        return;
      }
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
      showPlaces(map, s.places);
      map.getCanvas().style.cursor = s.siteMode ? "crosshair" : "";
      showHeat(map, s.heat);
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
  }, [p.year, p.heat, p.filters, p.selectedId, p.focusIds, p.places, p.siteMode]);

  // site check: circle, centre, and a state on every unit inside or outside it
  const siteIds = useRef<number[]>([]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready.current) return;
    const src = map.getSource("site") as maplibregl.GeoJSONSource | undefined;
    for (const id of siteIds.current) map.removeFeatureState({ source: SRC, id }, "site");
    siteIds.current = [];
    if (!p.site) {
      src?.setData({ type: "FeatureCollection", features: [] });
      return;
    }
    const { lon, lat, radius, comp, inside } = p.site;
    src?.setData({
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: {}, geometry: circlePolygon(lon, lat, radius) },
        { type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } },
      ],
    });
    const ids = allIds.current;
    for (const id of ids) {
      map.setFeatureState({ source: SRC, id }, { site: comp.has(id) ? "comp" : inside.has(id) ? "in" : "out" });
    }
    siteIds.current = ids;
  }, [p.site]);

  // pins that show at every zoom: a site check's competitors, or every branch of a searched brand
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready.current || !map.getLayer("unit-badge-comp")) return;
    const ids = p.site ? [...p.site.comp] : p.filters.brandIds ?? [];
    map.setFilter("unit-badge-comp", ["all", ["!=", ["slice", ["get", "l"], p.year - YEARS[0], p.year - YEARS[0] + 1], "0"], ["in", ["get", "id"], ["literal", ids]]]);
  }, [p.site, p.filters, p.year]);

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

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !p.fit?.points.length) return;
    const b = new maplibregl.LngLatBounds();
    for (const pt of p.fit.points) b.extend(pt);
    const wide = window.innerWidth > 720;
    map.fitBounds(b, {
      padding: wide ? { top: 90, bottom: 130, left: 360, right: 60 } : { top: 200, bottom: 130, left: 30, right: 30 },
      maxZoom: 16.6,
      duration: 900,
    });
  }, [p.fit]);

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

let heatLayers: string[] = [];

function addHeat(map: MLMap, hm: { tiles: HeatTile[] }) {
  // the wash sits under the basemap's labels so street names stay readable
  const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
  heatLayers = hm.tiles.map((t, i) => {
    const id = `heat-${i}`;
    map.addSource(id, { type: "image", url: heatUrl(t.image), coordinates: t.bounds });
    map.addLayer(
      {
        id,
        type: "raster",
        source: id,
        paint: { "raster-opacity": 0, "raster-fade-duration": 0, "raster-resampling": "linear" },
        layout: { visibility: "none" },
      },
      firstLabel,
    );
    return id;
  });
}

function showHeat(map: MLMap, on: boolean) {
  for (const id of heatLayers) {
    if (!map.getLayer(id)) continue;
    if (on) map.setLayoutProperty(id, "visibility", "visible");
    map.setPaintProperty(id, "raster-opacity", on ? 1 : 0);
  }
  if (!on) {
    // hide after the fade so the hidden layers cost nothing
    window.setTimeout(() => {
      for (const id of heatLayers)
        if (map.getLayer(id) && map.getPaintProperty(id, "raster-opacity") === 0) map.setLayoutProperty(id, "visibility", "none");
    }, 500);
  }
}
