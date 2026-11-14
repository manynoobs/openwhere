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
import { CUISINE_LABEL, DEFAULT_FILTERS, normName, YEARS, type Filters, type Meta, type UnitProps } from "./types";

type FullMeta = Meta & { heat: Meta["heat"] & { stops: [number, string][] }; district?: string };
type Hover = { x: number; y: number; props?: UnitProps; lngLat: [number, number] } | null;

const LAST = YEARS[YEARS.length - 1];
const listedNow = (u: UnitProps) => u.l[u.l.length - 1] === "1";
const COMPARE_RADIUS = 200; // metres, for the same-cuisine count in Compare

// one-click examples under the search box; shops are found by address so a data rebuild can't break them
const EXAMPLE_SHOPS = [
  { label: "100 Portland St", start: "G/F, 100 PORTLAND STREET" },
  { label: "11A Hau Fook", start: "GROUND FLOOR, 11A HAU FOOK STREET" },
];
const EXAMPLE_BRAND = "McDonald’s";

/** does the unit pass the filters in the year at index i (the same rules as the map's filter) */
function passes(u: UnitProps, i: number, f: Filters, brandIds: Set<number> | null) {
  const l = u.l[i];
  if (l === "0") return false;
  if (brandIds) {
    if (!brandIds.has(u.id)) return false;
  } else if (f.streetOnly && !u.sl) return false;
  if (f.cuisine && u.cu !== f.cuisine) return false;
  if (f.price >= 0 && u.pr !== f.price) return false;
  if (f.type === "RR" && !u.rr) return false;
  if (f.type === "RL" && u.rr) return false;
  if (f.seat && !u.seat) return false;
  if (f.prevOnly && l !== "2") return false;
  if (f.minChanges && Number(u.c[i]) < f.minChanges) return false;
  return true;
}

const median = (xs: number[]) => {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.floor((s.length - 1) / 2)];
};

/** what the address bar carries so a view can be shared: #shop=399 or #site=lon,lat,radius,cuisine, plus &mode=lifespan */
function readHash() {
  const q = new URLSearchParams(window.location.hash.slice(1));
  const site = q.get("site")?.split(",");
  return {
    shop: q.has("shop") ? Number(q.get("shop")) : null,
    site: site && site.length >= 3 && site.slice(0, 3).every((x) => Number.isFinite(Number(x)))
      ? { lon: Number(site[0]), lat: Number(site[1]), radius: Math.min(500, Math.max(50, Number(site[2]))), cuisine: site[3] in CUISINE_LABEL ? site[3] : "" }
      : null,
    lifespan: q.get("mode") === "lifespan",
  };
}

export default function App() {
  const [meta, setMeta] = useState<FullMeta | null>(null);
  const [all, setAll] = useState<UnitProps[]>([]);
  const [year, setYear] = useState<number>(LAST);
  const [playing, setPlaying] = useState(false);
  const [pulse, setPulse] = useState(0);
  const [heat, setHeatOn] = useState(false);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<UnitProps | null>(null);
  const [pinned, setPinned] = useState<number[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [fly, setFly] = useState<FlyTarget | null>(null);
  const [fit, setFit] = useState<{ points: [number, number][]; key: number } | null>(null);
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
    if ((heat || siteOpen || pinned.length > 0) && !grid) loadHeatGrid().then(setGrid);
  }, [heat, siteOpen, pinned, grid]);

  // shop lifespan covers the whole ten years, so the year bar steps aside and the pins show today
  const setHeat = useCallback((on: boolean) => {
    setHeatOn(on);
    if (on) {
      setPlaying(false);
      setYear(LAST);
    }
  }, []);
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

  // a brand typed into Filters: every unit whose current or last sign contains it
  const brandIds = useMemo(() => {
    const q = normName(filters.brand);
    if (q.length < 2) return null;
    return all.filter((u) => normName(u.s ?? "").includes(q)).map((u) => u.id);
  }, [all, filters.brand]);
  const mapFilters = useMemo<Filters>(() => ({ ...filters, brandIds }), [filters, brandIds]);
  // once typing pauses, frame every branch
  useEffect(() => {
    if (!brandIds?.length) return;
    const t = window.setTimeout(() => {
      const ids = new Set(brandIds);
      const points = all.filter((u) => ids.has(u.id)).map((u) => [u.lon!, u.lat!] as [number, number]);
      setFit({ points, key: Date.now() });
    }, 450);
    return () => window.clearTimeout(t);
  }, [brandIds, all]);

  // the typical spot: around each restaurant listed now, how many others (of the chosen cuisine) are within the radius
  const typical = useMemo(() => {
    if (!siteOpen) return null;
    const now = all.filter(listedNow);
    const rivals = site.cuisine ? now.filter((u) => u.cu === site.cuisine) : now;
    return median(
      now.map((u) => {
        let n = 0;
        for (const r of rivals) if (r.id !== u.id && metres(u.lon!, u.lat!, r.lon!, r.lat!) <= site.radius) n += 1;
        return n;
      }),
    );
  }, [siteOpen, all, site.radius, site.cuisine]);

  const siteResult = useMemo<SiteResult | null>(() => {
    if (!siteOpen || site.lon == null || site.lat == null) return null;
    const { lon, lat, radius } = site;
    const near = all
      .map((u) => ({ ...u, dist: metres(lon, lat, u.lon!, u.lat!) }))
      .filter((u) => u.dist <= radius)
      .sort((a, b) => a.dist - b.dist);
    const now = near.filter(listedNow);
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
    const ids = brandIds ? new Set(brandIds) : null;
    return all.filter((u) => passes(u, year - YEARS[0], filters, ids)).length;
  }, [all, year, filters, brandIds]);

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

  const open = useCallback((u: UnitProps) => {
    setSiteOpen(false);
    setSelected(u);
    if (!u.sl) setFilters((f) => (f.streetOnly ? { ...f, streetOnly: false } : f));
    if (u.lon != null && u.lat != null) setFly({ lon: u.lon, lat: u.lat, key: Date.now() });
  }, []);

  const examples = useMemo(
    () => EXAMPLE_SHOPS.map((e) => ({ ...e, unit: all.find((u) => u.en.startsWith(e.start)) })).filter((e) => e.unit),
    [all],
  );

  // what Compare adds for each pinned shopfront: price, MTR, how long shops last nearby, same-cuisine shops around it
  const compareFacts = useMemo(() => {
    const now = all.filter(listedNow);
    return Object.fromEntries(
      pinned.flatMap((id) => {
        const u = byId.get(id);
        if (!u) return [];
        const on = listedNow(u);
        const cu = on && u.cu && u.cu !== "unknown" ? u.cu : "";
        const life = grid ? heatAt(grid, u.lon!, u.lat!) : null;
        return [[id, {
          price: on && u.pr >= 0 ? meta?.price_bands[u.pr] ?? null : null,
          listed: on,
          mtr: u.mtr,
          mtrx: u.mtrx,
          life: life?.v ?? null,
          cuisine: cu ? CUISINE_LABEL[cu] : "",
          rivals: now.filter((r) => r.id !== id && (!cu || r.cu === cu) && metres(u.lon!, u.lat!, r.lon!, r.lat!) <= COMPARE_RADIUS).length,
        }]];
      }),
    );
  }, [pinned, byId, all, grid, meta]);

  // shareable view: read the address once the shops are loaded, then keep it in step
  const hashRead = useRef(false);
  useEffect(() => {
    if (!all.length) return;
    const apply = () => {
      const h = readHash();
      if (h.lifespan) setHeat(true);
      const u = h.shop != null ? byId.get(h.shop) : undefined;
      if (u) open(u);
      else if (h.site) {
        setSite(h.site);
        setSelected(null);
        setSiteOpen(true);
        setFly({ lon: h.site.lon, lat: h.site.lat, key: Date.now() });
      }
      hashRead.current = true;
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, [all, byId, open, setHeat]);
  useEffect(() => {
    if (!hashRead.current) return;
    const parts: string[] = [];
    if (selected) parts.push(`shop=${selected.id}`);
    else if (siteOpen && site.lon != null && site.lat != null)
      parts.push(`site=${site.lon.toFixed(5)},${site.lat.toFixed(5)},${site.radius}${site.cuisine ? `,${site.cuisine}` : ""}`);
    if (heat) parts.push("mode=lifespan");
    const hash = parts.length ? `#${parts.join("&")}` : "";
    if (hash !== window.location.hash) history.replaceState(null, "", hash || window.location.pathname + window.location.search);
  }, [selected, siteOpen, site, heat]);

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
          filters={mapFilters}
          heatMeta={meta.heat}
          selectedId={selected?.id ?? null}
          focusIds={focusIds}
          fly={fly}
          fit={fit}
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
            if (props) open(props);
          }}
        />
        {examples.length > 0 && !selected && !siteOpen && (
          <div className="examples">
            {examples.map((e) => (
              <button key={e.label} onClick={() => open(e.unit!)}>
                <PinMark n={e.unit!.chg} size={15} />
                {e.label}
              </button>
            ))}
            <button
              aria-pressed={normName(filters.brand) === normName(EXAMPLE_BRAND)}
              onClick={() => setFilters((f) => ({ ...f, brand: normName(f.brand) === normName(EXAMPLE_BRAND) ? "" : EXAMPLE_BRAND }))}
            >
              {EXAMPLE_BRAND}
            </button>
          </div>
        )}
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
          typical={typical}
          district={meta?.heat.district ?? null}
          counts={cuisineCounts}
          priceBands={meta?.price_bands ?? []}
          onChange={setSite}
          onClose={() => setSiteOpen(false)}
          onOpen={open}
        />
      )}
      <Legend heat={heat} stops={meta?.heat.stops ?? null} district={meta?.heat.district} year={year} />
      {!heat && <YearBar year={year} setYear={setYear} playing={playing} setPlaying={setPlaying} />}

      {pinned.length > 0 && !compareOpen && (
        <button className="iconbtn glass comparebtn" onClick={() => setCompareOpen(true)}>
          <Icon name="compare" />
          Compare <span className="count num">{pinned.length}</span>
        </button>
      )}
      {compareOpen && pinned.length > 0 && (
        <CompareSheet
          ids={pinned}
          facts={compareFacts}
          onClose={() => setCompareOpen(false)}
          onUnpin={(id) => setPinned((p) => p.filter((x) => x !== id))}
          onOpen={(u) => {
            const props = byId.get(u.id);
            if (props) open(props);
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
      <PrintSheet ids={pinned} facts={compareFacts} />
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
