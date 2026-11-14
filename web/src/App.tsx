import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapView, type FlyTarget } from "./map/MapView";
import { Search } from "./components/Search";
import { Controls } from "./components/Controls";
import { Legend, YearBar } from "./components/Bottom";
import { UnitPanel } from "./components/UnitPanel";
import { CompareSheet, PrintSheet } from "./components/Compare";
import { Icon } from "./components/Icon";
import { heatAt, loadHeatGrid, loadMeta, type HeatGrid } from "./data";
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

  useEffect(() => {
    loadMeta().then(setMeta).catch((e: Error) => setFailed(e.message));
  }, []);
  useEffect(() => {
    if (heat && !grid) loadHeatGrid().then(setGrid);
  }, [heat, grid]);

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
    <div className={panelOpen ? "panel-open" : ""} style={{ height: "100%" }}>
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
        />
      )}

      <div className="topleft glass">
        <div className="brand">
          <h1>
            Shopfront Past Lives <span className="tc">鋪位前世</span>
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

      <Controls heat={heat} setHeat={setHeat} filters={filters} setFilters={setFilters} shown={shown} meta={meta} />
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
        onPin={togglePin}
        onClose={() => setSelected(null)}
      />

      {hover && <Tooltip hover={hover} heat={heat} grid={grid} year={year} />}
      <PrintSheet ids={pinned} />
    </div>
  );
}

function Tooltip({ hover, heat, grid, year }: { hover: NonNullable<Hover>; heat: boolean; grid: HeatGrid | null; year: number }) {
  const p = hover.props;
  if (p) {
    const n = Number(p.c[year - YEARS[0]]);
    return (
      <div className="tooltip glass" style={{ left: hover.x, top: hover.y }}>
        <b>{p.s || "Sign not recorded"}</b>
        <div className="muted num">
          {n === 1 ? "1 store change" : `${n} store changes`} {year < LAST ? `by end of ${year}` : "since 2016"}
        </div>
      </div>
    );
  }
  if (heat && grid) {
    const h = heatAt(grid, year, hover.lngLat[0], hover.lngLat[1]);
    if (!h || h.v == null) return null;
    return (
      <div className="tooltip glass num" style={{ left: hover.x, top: hover.y }}>
        <b>≈{h.v.toFixed(2)} changes per shop</b>
        <div className="muted">about {h.n} street-level shops nearby</div>
      </div>
    );
  }
  return null;
}
