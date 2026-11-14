import { useEffect, useRef, useState } from "react";
import { DEFAULT_FILTERS, type Filters, type Meta } from "../types";
import { monthYear } from "../data";
import { Icon } from "./Icon";

interface Props {
  heat: boolean;
  setHeat: (on: boolean) => void;
  filters: Filters;
  setFilters: (f: Filters) => void;
  shown: number;
  meta: Meta | null;
}

export function Controls({ heat, setHeat, filters, setFilters, shown, meta }: Props) {
  const [open, setOpen] = useState<"filters" | "about" | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const active =
    (filters.streetOnly ? 0 : 1) + (filters.type !== "all" ? 1 : 0) + (filters.seat ? 1 : 0) + (filters.prevOnly ? 1 : 0) + (filters.minChanges ? 1 : 0);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(null);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(null);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const set = (patch: Partial<Filters>) => setFilters({ ...filters, ...patch });

  return (
    <div className="topright" ref={box}>
      <div className="segmented glass" role="group" aria-label="Map mode">
        <button aria-pressed={!heat} onClick={() => setHeat(false)}>Shops</button>
        <button aria-pressed={heat} onClick={() => setHeat(true)}>Change heat</button>
      </div>
      <div style={{ position: "relative" }}>
        <button className="iconbtn glass" aria-expanded={open === "filters"} onClick={() => setOpen(open === "filters" ? null : "filters")}>
          <Icon name="filter" />
          Filters
          {active > 0 && <span className="count num">{active}</span>}
        </button>
        {open === "filters" && (
          <div className="popover glass" role="dialog" aria-label="Filters">
            <div className="fgroup">
              <h2>Floors</h2>
              <div className="fseg">
                <button aria-pressed={filters.streetOnly} onClick={() => set({ streetOnly: true })}>Street level</button>
                <button aria-pressed={!filters.streetOnly} onClick={() => set({ streetOnly: false })}>All floors</button>
              </div>
            </div>
            <div className="fgroup">
              <h2>Licence types recorded</h2>
              <div className="fseg">
                <button aria-pressed={filters.type === "all"} onClick={() => set({ type: "all" })}>Any</button>
                <button aria-pressed={filters.type === "RL"} onClick={() => set({ type: "RL" })} title="A general restaurant licence was recorded at some point">
                  General
                </button>
                <button aria-pressed={filters.type === "RR"} onClick={() => set({ type: "RR" })} title="Only light refreshment licences were ever recorded">
                  Light only
                </button>
              </div>
            </div>
            <div className="fgroup">
              <h2>Store changes since 2016</h2>
              <div className="fseg">
                {[0, 1, 2, 3, 4].map((n) => (
                  <button key={n} aria-pressed={filters.minChanges === n} onClick={() => set({ minChanges: n })}>
                    {n === 0 ? "Any" : `${n}+`}
                  </button>
                ))}
              </div>
            </div>
            <div className="fgroup">
              <label className="toggle">
                Previously licensed, none listed now
                <span className="switch">
                  <input type="checkbox" checked={filters.prevOnly} onChange={(e) => set({ prevOnly: e.target.checked })} />
                  <span />
                </span>
              </label>
              <label className="toggle">
                Outside seating ever recorded
                <span className="switch">
                  <input type="checkbox" checked={filters.seat} onChange={(e) => set({ seat: e.target.checked })} />
                  <span />
                </span>
              </label>
            </div>
            <div className="pfoot">
              <span className="num">{shown.toLocaleString()} shopfronts shown</span>
              <button className="linkbtn" disabled={active === 0 && filters.streetOnly} onClick={() => setFilters(DEFAULT_FILTERS)}>
                Reset
              </button>
            </div>
          </div>
        )}
      </div>
      <div style={{ position: "relative" }}>
        <button className="iconbtn glass square" aria-label="About the data" aria-expanded={open === "about"} onClick={() => setOpen(open === "about" ? null : "about")}>
          <Icon name="info" />
        </button>
        {open === "about" && meta && <About meta={meta} />}
      </div>
    </div>
  );
}

function About({ meta }: { meta: Meta & { district?: string; district_detail?: string; street_units_total?: number; street_units_mapped?: number; gap_threshold_months?: number } }) {
  const coverage = meta.street_units_total ? Math.round((100 * (meta.street_units_mapped ?? 0)) / meta.street_units_total) : null;
  return (
    <div className="about glass" role="dialog" aria-label="About the data">
      <h2>About the data</h2>
      <p>
        Every point is a shopfront that has held a restaurant licence in {meta.district_detail}. The counts come from the
        Food and Environmental Hygiene Department’s licence lists, one archived file per month from{" "}
        {monthYear(meta.first_file)} to {monthYear(meta.latest_file)}.
      </p>
      <p>
        A <b>store change</b> is a shop with a different sign listed at an address after the previous one stopped being listed.
      </p>
      <p>
        <b>Change heat</b> shows store changes per street-level shop, smoothed over about 100 m. Streets with fewer than five
        shops nearby are left blank.
      </p>
      <dl className="num">
        <dt>Monthly files read (English and Chinese)</dt>
        <dd>{meta.files_good}</dd>
        <dt>Files set aside as damaged</dt>
        <dd>{meta.files_quarantined}</dd>
        <dt>Shopfronts on the map</dt>
        <dd>{meta.units.toLocaleString()}</dd>
        <dt>Street-level shopfronts placed</dt>
        <dd>{coverage != null ? `${meta.street_units_mapped?.toLocaleString()} of ${meta.street_units_total?.toLocaleString()} (${coverage}%)` : "–"}</dd>
      </dl>
      <p className="fine">
        From FEHD licence lists. Not a record of ownership, tenancy or business performance.
      </p>
    </div>
  );
}
