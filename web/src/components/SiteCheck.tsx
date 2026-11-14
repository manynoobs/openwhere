import { useState } from "react";
import { CUISINES, CUISINE_LABEL, type UnitProps } from "../types";
import type { HeatGrid } from "../data";
import { heatAt } from "../data";
import { PLACE_PATH, type PlaceKind } from "../map/places";
import { Icon } from "./Icon";
import { PinMark } from "./PinMark";

export interface Place {
  k: PlaceKind;
  en: string;
  tc: string;
  st?: string;
  lon: number;
  lat: number;
}

export interface SiteState {
  lon: number | null;
  lat: number | null;
  radius: number;
  cuisine: string; // "" = any cuisine
}

export interface SiteResult {
  inside: (UnitProps & { dist: number })[]; // units listed now within the radius, nearest first
  comp: (UnitProps & { dist: number })[]; // same cuisine, within the radius
  prev: number; // previously licensed, none listed now
  general: number;
  light: number;
  places: Record<PlaceKind, number>;
  mtr: (Place & { dist: number }) | null;
}

interface Props {
  site: SiteState;
  result: SiteResult | null;
  grid: HeatGrid | null;
  /** the same count around a typical restaurant in the district, to read this spot against */
  typical: number | null;
  /** the district's own share of new shops lasting three years */
  district: number | null;
  counts: Record<string, number>;
  priceBands: string[];
  onChange: (s: SiteState) => void;
  onOpen: (u: UnitProps) => void;
  onClose: () => void;
}

const PLACE_WORD: Partial<Record<PlaceKind, [string, string]>> & Record<"hotel" | "school" | "mall" | "landmark" | "transit", [string, string]> = {
  hotel: ["hotel", "hotels"],
  school: ["school", "schools"],
  mall: ["mall", "malls"],
  landmark: ["landmark", "landmarks"],
  transit: ["station", "stations"],
};

const metres = (m: number) => (m < 1000 ? `${Math.round(m / 5) * 5} m` : `${(m / 1000).toFixed(1)} km`);

function PlaceIcon({ k }: { k: PlaceKind }) {
  return (
    <svg width={16} height={16} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PLACE_PATH[k]} />
    </svg>
  );
}

const SHORT = 4; // rows shown before "Show all"

export function SiteCheck({ site, result, grid, typical, district, counts, priceBands, onChange, onOpen, onClose }: Props) {
  const [showAll, setShowAll] = useState(false);
  const list = result ? (site.cuisine ? result.comp : result.inside) : [];
  const label = site.cuisine ? CUISINE_LABEL[site.cuisine] : "";
  const life = grid && site.lon != null && site.lat != null ? heatAt(grid, site.lon, site.lat) : null;
  return (
    <section className="sitecard glass" aria-label="Site check">
      <header className="site-head">
        <h2>Site check</h2>
        <button className="close" aria-label="Close site check" onClick={onClose}>
          <Icon name="close" size={16} />
        </button>
      </header>

      <div className="site-controls">
        <label className="site-field">
          <span>Your cuisine</span>
          <select value={site.cuisine} onChange={(e) => onChange({ ...site, cuisine: e.target.value })}>
            <option value="">Any cuisine</option>
            {CUISINES.map(([k, l]) => (
              <option key={k} value={k}>
                {l} ({counts[k] ?? 0})
              </option>
            ))}
          </select>
        </label>
        <label className="site-field">
          <span>
            Radius <b className="num">{site.radius} m</b>
          </span>
          <input
            type="range"
            min={50}
            max={500}
            step={25}
            value={site.radius}
            onChange={(e) => onChange({ ...site, radius: Number(e.target.value) })}
            aria-label="Radius in metres"
          />
        </label>
      </div>

      {site.lon == null || !result ? (
        <p className="site-hint">
          <Icon name="target" size={18} />
          Click a spot on the map to check it
        </p>
      ) : (
        <div className="site-body">
          <div className="site-lead">
            <span className="site-big num">{site.cuisine ? result.comp.length : result.inside.length}</span>
            <span>
              {site.cuisine ? (
                <>
                  <b>{label}</b> {result.comp.length === 1 ? "shop" : "shops"} listed now within {site.radius} m
                </>
              ) : (
                <>restaurants listed now within {site.radius} m</>
              )}
            </span>
          </div>

          {typical != null && <Benchmark n={list.length} typical={typical} radius={site.radius} what={label ? `${label} shops` : "restaurants"} />}

          {list.length > 0 && (
            <ul className="site-list">
              {(showAll ? list : list.slice(0, SHORT)).map((u) => (
                <li key={u.id}>
                  <button onClick={() => onOpen(u)}>
                    <PinMark n={u.chg} size={18} />
                    <span className="site-name">
                      {u.s || "Sign not recorded"}
                      <small>{u.pr >= 0 ? priceBands[u.pr] : "No price data"}</small>
                    </span>
                    <span className="site-dist num">{metres(u.dist)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {list.length > SHORT && (
            <button className="linkbtn site-more num" onClick={() => setShowAll(!showAll)}>
              {showAll ? "Show nearest 4" : `Show all ${list.length}`}
            </button>
          )}

          <Prices shops={list} bands={priceBands} cuisine={label} />

          <dl className="site-stats num">
            {site.cuisine && (
              <div>
                <dt>All restaurants listed now</dt>
                <dd>{result.inside.length}</dd>
              </div>
            )}
            <div>
              <dt>New shops here lasting 3 years</dt>
              <dd>
                {life && life.v != null ? `${Math.round(life.v * 100)}%` : "Too few shops"}
                {life && life.v != null && district != null && <small> · district {Math.round(district * 100)}%</small>}
              </dd>
            </div>
            <div>
              <dt>Licensed before, none listed now</dt>
              <dd>{result.prev}</dd>
            </div>
            <div>
              <dt>Licences listed now</dt>
              <dd>
                {result.general} general · {result.light} light refreshment
              </dd>
            </div>
            {result.mtr && (
              <div>
                <dt>Nearest MTR exit</dt>
                <dd>
                  {metres(result.mtr.dist)} <small>{[result.mtr.st, result.mtr.en].filter(Boolean).join(" ")}</small>
                </dd>
              </div>
            )}
          </dl>

          <div className="site-places">
            {(["hotel", "school", "mall", "landmark", "transit"] as const).map((k) => (
              <span key={k} title={k}>
                <PlaceIcon k={k} />
                <b className="num">{result.places[k]}</b>
                {PLACE_WORD[k][result.places[k] === 1 ? 0 : 1]}
              </span>
            ))}
          </div>

          <p className="fine">
            Price and cuisine from OpenRice where a listing matched; otherwise cuisine is guessed from the shop’s name. Distances
            are straight-line. Places from OpenStreetMap.
          </p>
        </div>
      )}
    </section>
  );
}

/** This spot's count read against the typical restaurant's surroundings in the district. */
function Benchmark({ n, typical, radius, what }: { n: number; typical: number; radius: number; what: string }) {
  const verdict = n >= typical * 1.5 && n - typical >= 2 ? "More than usual" : n <= typical / 1.5 && typical - n >= 2 ? "Fewer than usual" : "About usual";
  return (
    <p className="site-bench num">
      <b>{verdict}.</b> A typical restaurant in Yau Tsim has {typical} other {what} within {radius} m
    </p>
  );
}

/** What nearby shops charge per person (OpenRice), as one bar per price band. */
function Prices({ shops, bands, cuisine }: { shops: UnitProps[]; bands: string[]; cuisine: string }) {
  if (!shops.length || !bands.length) return null;
  const counts = bands.map((_, i) => shops.filter((u) => u.pr === i).length);
  const known = counts.reduce((a, b) => a + b, 0);
  const max = Math.max(1, ...counts);
  return (
    <div className="site-prices">
      <h3>What {cuisine ? `${cuisine} shops` : "they"} charge per person</h3>
      {known === 0 ? (
        <p className="fine">No price data for these shops.</p>
      ) : (
        <ul>
          {bands.map((b, i) => (
            <li key={b} className={counts[i] ? "" : "zero"}>
              <span className="pl num">{b}</span>
              <span className="pb">
                <i style={{ width: `${(counts[i] / max) * 100}%` }} />
              </span>
              <span className="pc num">{counts[i]}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="fine num">
        {known} of {shops.length} have a price on OpenRice{shops.length - known ? `; ${shops.length - known} no data` : ""}.
      </p>
    </div>
  );
}
