import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapView, type FlyTarget } from "./map/MapView";
import { Search } from "./components/Search";
import { Controls } from "./components/Controls";
import { Legend, YearBar } from "./components/Bottom";
import { UnitPanel } from "./components/UnitPanel";
import { CompareSheet, PrintSheet } from "./components/Compare";
import { Icon } from "./components/Icon";
import { PinMark } from "./components/PinMark";
import { LogoMark } from "./components/Logo";
import { dataUrl, heatAt, loadHeatGrid, loadMeta, type HeatGrid } from "./data";
import { SiteCheck, type Place, type SiteResult, type SiteState } from "./components/SiteCheck";
import { metres } from "./map/geo";
import { PLACE_KINDS, PLACE_LABEL, type PlaceKind } from "./map/places";
import { DEFAULT_FILTERS, YEARS, type Filters, type Meta, type UnitProps } from "./types";

type FullMeta = Meta & { heat: Meta["heat"] & { stops: [number, string][] }; district?: string };
type Hover = { x: number; y: number; props?: UnitProps; lngLat: [number, number] } | null;

const LAST = YEARS[YEARS.length - 1];

export default function App() {
  const [meta, setMeta] = useState<FullMeta | null>(null);
  const [all, setAll] = useState<UnitProps[]>([]);
  const [year, setYear] = useState<number>(LAST);
  const [playing, setPlaying] = useState(false);
  const [pulse, setPulse] = useState(0);
  const [heat, setHeat] = useState(false);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<UnitProps | null>(null);
  const [pinned, setPinned] = useState<number[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [fly, setFly] = useState<FlyTarget | null>(null);
  const [hover, setHover] = useState<Hover>(null);
  const [grid, setGrid] = useState<HeatGrid | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [placesOn, setPlacesOn] = useState(false);
  const [places, setPlaces] = useState<Place[]>([]);
  const [siteOpen, setSiteOpen] = useState(false);
  const [site, setSite] = useState<SiteState>({ lon: null, lat: null, radius: 200, cuisine: "" });
  const [placeHover, setPlaceHover] = useState<{ x: number; y: number; name: string; kind: string } | null>(null);

  useEffect(() => {
    loadMeta().then(setMeta).catch((e: Error) => setFailed(e.message));
  }, []);
  useEffect(() => {
    if ((heat || siteOpen) && !grid) loadHeatGrid().then(setGrid);
  }, [heat, siteOpen, grid]);
  useEffect(() => {
    fetch(dataUrl("facilities.geojson"))
      .then((r) => r.json())
      .then((g) =>
        setPlaces(
          g.features.map((f: { properties: Omit<Place, "lon" | "lat">; geometry: { coordinates: [number, number] } }) => ({
            ...f.properties,
            lon: f.geometry.coordinates[0],
            lat: f.geometry.coordinates[1],
          })),
        ),
      );
  }, []);

  // cuisine counts across the district, for the site check menu
  const cuisineCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const u of all) if (u.cu) c[u.cu] = (c[u.cu] ?? 0) + 1;
    return c;
  }, [all]);

  const siteResult = useMemo<SiteResult | null>(() => {
    if (!siteOpen || site.lon == null || site.lat == null) return null;
    const { lon, lat, radius } = site;
    const near = all
      .map((u) => ({ ...u, dist: metres(lon, lat, u.lon!, u.lat!) }))
      .filter((u) => u.dist <= radius)
      .sort((a, b) => a.dist - b.dist);
    const now = near.filter((u) => u.l[u.l.length - 1] === "1");
    const counts = Object.fromEntries(PLACE_KINDS.map((k) => [k, 0])) as Record<PlaceKind, number>;
    let mtr: SiteResult["mtr"] = null;
    for (const p of places) {
      const d = metres(lon, lat, p.lon, p.lat);
      if (d <= radius) counts[p.k] += 1;
      if (p.k === "mtr" && (!mtr || d < mtr.dist)) mtr = { ...p, dist: d };
    }
    return {
      inside: now,
      comp: site.cuisine ? now.filter((u) => u.cu === site.cuisine) : [],
      prev: near.filter((u) => u.l[u.l.length - 1] === "2").length,
      general: now.filter((u) => u.t === "RL").length,
      light: now.filter((u) => u.t === "RR").length,
      places: counts,
      mtr,
    };
  }, [siteOpen, site, all, places]);

  const siteForMap = useMemo(() => {
    if (!siteResult || site.lon == null || site.lat == null) return null;
    return {
      lon: site.lon,
      lat: site.lat,
      radius: site.radius,
      comp: new Set(siteResult.comp.map((u) => u.id)),
      inside: new Set(siteResult.inside.map((u) => u.id)),
    };
  }, [siteResult, site]);

  // play: step a year at a time from 2016, pulse each step, stop at the latest year
  const timer = useRef<number>();
  useEffect(() => {
    if (!playing) return;
    let y = year >= LAST ? YEARS[0] : year;
    setYear(y);
    setPulse((p) => p + 1);
    timer.current = window.setInterval(() => {
      y += 1;
      if (y > LAST) {
        setPlaying(false);
        return;
      }
      setYear(y);
      setPulse((p) => p + 1);
    }, 1100);
    return () => window.clearInterval(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  const shown = useMemo(() => {
    const i = year - YEARS[0];
    return all.filter((u) => {
      const l = u.l[i];
      if (l === "0") return false;
      if (filters.streetOnly && !u.sl) return false;
      if (filters.type === "RR" && !u.rr) return false;
      if (filters.type === "RL" && u.rr) return false;
      if (filters.seat && !u.seat) return false;
      if (filters.prevOnly && l !== "2") return false;
      if (filters.minChanges && Number(u.c[i]) < filters.minChanges) return false;
      return true;
    }).length;
  }, [all, year, filters]);

  const select = useCallback((id: number | null, props?: UnitProps, at?: [number, number]) => {
    if (id == null || !props) {
      setSelected(null);
      return;
    }
    setSelected(props);
    if (at) setFly({ lon: at[0], lat: at[1], key: Date.now() });
  }, []);

  const byId = useMemo(() => new Map(all.map((u) => [u.id, u])), [all]);
  const panelOpen = selected != null;
  const togglePin = () => {
    if (!selected) return;
    setPinned((p) => (p.includes(selected.id) ? p.filter((x) => x !== selected.id) : p.length >= 3 ? p : [...p, selected.id]));
  };
  const focusIds = useMemo(() => pinned, [pinned]);

  if (failed) {
    return (
      <div className="topleft glass" style={{ padding: 16 }}>
        The map data could not be loaded ({failed}). Run the pipeline, then reload.
      </div>
    );
  }

  return (
    <div
      className={`${panelOpen ? "panel-open" : ""} ${compareOpen && pinned.length ? "compare-open" : ""} ${siteOpen ? "site-open" : ""}`}
      style={{ height: "100%" }}
    >
      {meta && (
        <MapView
          year={year}
          heat={heat}
          filters={filters}
          heatMeta={meta.heat}
          selectedId={selected?.id ?? null}
          focusIds={focusIds}
          fly={fly}
          pulse={pulse}
          panelOpen={panelOpen}
          onSelect={select}
          onHover={setHover}
          onReady={setAll}
          places={placesOn}
          site={siteForMap}
          siteMode={siteOpen}
          onSitePick={(lon, lat, props) => setSite((s) => ({ ...s, lon, lat, cuisine: s.cuisine || (props?.cu && props.cu !== "unknown" ? props.cu : "") }))}
          onPlaceHover={setPlaceHover}
        />
      )}

      <div className="topleft glass">
        <div className="brand">
          <h1>
            <LogoMark size={20} />
            <span>
              <b>Open</b>Where
            </span>
          </h1>
          <span className="where">{meta?.district ?? "Yau Tsim"} · 2016–2026</span>
        </div>
        <Search
          district={meta?.district ?? "Yau Tsim"}
          onPick={(r) => {
            const props = byId.get(r[0]);
            if (props) {
              setSelected(props);
              setFly({ lon: r[5], lat: r[6], key: Date.now() });
              if (!props.sl && filters.streetOnly) setFilters({ ...filters, streetOnly: false });
            }
          }}
        />
      </div>

      <Controls
        heat={heat}
        setHeat={setHeat}
        filters={filters}
        setFilters={setFilters}
        shown={shown}
        meta={meta}
        places={placesOn}
        setPlaces={setPlacesOn}
        siteOpen={siteOpen}
        setSiteOpen={(on) => {
          setSiteOpen(on);
          if (on) setSelected(null);
        }}
      />
      {siteOpen && (
        <SiteCheck
          site={site}
          result={siteResult}
          grid={grid}
          counts={cuisineCounts}
          priceBands={meta?.price_bands ?? []}
          onChange={setSite}
          onClose={() => setSiteOpen(false)}
          onOpen={(u) => {
            setSiteOpen(false);
            setSelected(u);
            if (u.lon != null && u.lat != null) setFly({ lon: u.lon, lat: u.lat, key: Date.now() });
          }}
        />
      )}
      <Legend heat={heat} stops={meta?.heat.stops ?? null} year={year} />
      <YearBar year={year} setYear={setYear} playing={playing} setPlaying={setPlaying} />

      {pinned.length > 0 && !compareOpen && (
        <button className="iconbtn glass comparebtn" onClick={() => setCompareOpen(true)}>
          <Icon name="compare" />
          Compare <span className="count num">{pinned.length}</span>
        </button>
      )}
      {compareOpen && pinned.length > 0 && (
        <CompareSheet
          ids={pinned}
          onClose={() => setCompareOpen(false)}
          onUnpin={(id) => setPinned((p) => p.filter((x) => x !== id))}
          onOpen={(u) => {
            const props = byId.get(u.id);
            if (props) {
              setSelected(props);
              setFly({ lon: u.lon, lat: u.lat, key: Date.now() });
            }
          }}
        />
      )}

      <UnitPanel
        id={selected?.id ?? null}
        props={selected}
        pinned={selected ? pinned.includes(selected.id) : false}
        canPin={pinned.length < 3}
        priceBands={meta?.price_bands ?? []}
        onPin={togglePin}
        onClose={() => setSelected(null)}
        onCheck={(u) => {
          setSite((s) => ({ ...s, lon: u.lon ?? null, lat: u.lat ?? null, cuisine: u.cu && u.cu !== "unknown" ? u.cu : s.cuisine }));
          setSelected(null);
          setSiteOpen(true);
        }}
      />

      {hover && !placeHover && <Tooltip hover={hover} heat={heat} grid={grid} year={year} priceBands={meta?.price_bands ?? []} />}
      {placeHover && (
        <div className="tooltip glass" style={{ left: placeHover.x, top: placeHover.y }}>
          <div>
            <b>{placeHover.name || PLACE_LABEL[placeHover.kind as PlaceKind]}</b>
            <div className="muted">{PLACE_LABEL[placeHover.kind as PlaceKind]}</div>
          </div>
        </div>
      )}
      <PrintSheet ids={pinned} />
    </div>
  );
}

function Tooltip({
  hover,
  heat,
  grid,
  year,
  priceBands,
}: {
  hover: NonNullable<Hover>;
  heat: boolean;
  grid: HeatGrid | null;
  year: number;
  priceBands: string[];
}) {
  const p = hover.props;
  if (p) {
    const n = Number(p.c[year - YEARS[0]]);
    return (
      <div className="tooltip glass" style={{ left: hover.x, top: hover.y }}>
        <PinMark n={n} size={22} hollow={p.l[year - YEARS[0]] === "2"} />
        <div>
          <b>{p.s || "Sign not recorded"}</b>
          <div className="muted num">
            {n === 1 ? "1 store change" : `${n} store changes`} {year < LAST ? `by end of ${year}` : "since 2016"}
            {p.l[p.l.length - 1] === "1" && priceBands[p.pr] ? ` · ${priceBands[p.pr]}` : ""}
          </div>
        </div>
      </div>
    );
  }
  if (heat && grid) {
    const h = heatAt(grid, hover.lngLat[0], hover.lngLat[1]);
    if (!h || h.v == null) return null;
    return (
      <div className="tooltip glass num" style={{ left: hover.x, top: hover.y }}>
        <div>
          <b>{Math.round(h.v * 100)}% of new shops here last 3 years</b>
          <div className="muted">
            {h.median != null ? `Half are gone within ${h.median.toFixed(1)} years` : "More than half are still listed"} · based on about{" "}
            {h.n} shops
          </div>
        </div>
      </div>
    );
  }
  return null;
}
