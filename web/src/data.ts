import type { Meta, SearchRow, UnitDetail } from "./types";

const url = (p: string) => new URL(`data/${p}`, document.baseURI).href;

async function json<T>(p: string): Promise<T> {
  const r = await fetch(url(p));
  if (!r.ok) throw new Error(`Could not load ${p} (${r.status})`);
  return r.json() as Promise<T>;
}

export const unitsUrl = url("units.geojson");
export const heatUrl = (year: number) => url(`heat/${year}.png`);
export const loadMeta = () => json<Meta & { heat: Meta["heat"] & { stops: [number, string][] } }>("meta.json");

const details = new Map<number, Promise<UnitDetail>>();
export function loadUnit(id: number) {
  if (!details.has(id)) details.set(id, json<UnitDetail>(`units/${id}.json`));
  return details.get(id)!;
}

let searchIndex: Promise<SearchRow[]> | null = null;
export const loadSearch = () => (searchIndex ??= json<SearchRow[]>("search.json"));

export interface HeatGrid {
  x0: number;
  y1: number;
  cell: number;
  w: number;
  h: number;
  years: Record<string, { v: (number | null)[]; n: number[] }>;
}
let heatGrid: Promise<HeatGrid> | null = null;
export const loadHeatGrid = () => (heatGrid ??= json<HeatGrid>("heat/grid.json"));

/** value and shops nearby at a lon/lat, from the 100 m readout grid */
export function heatAt(g: HeatGrid, year: number, lon: number, lat: number) {
  const R = 6378137;
  const x = (R * lon * Math.PI) / 180;
  const y = R * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const col = Math.floor((x - g.x0) / g.cell);
  const row = Math.floor((g.y1 - y) / g.cell);
  if (col < 0 || row < 0 || col >= g.w || row >= g.h) return null;
  const yr = g.years[String(year)];
  const i = row * g.w + col;
  return { v: yr.v[i], n: yr.n[i] };
}

// --- formatting -------------------------------------------------------------

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const monthYear = (iso: string) => `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${iso.slice(0, 4)}`;
export const yearOf = (iso: string) => iso.slice(0, 4);

const PLACEHOLDER = /^\(?\s*(no record( found)?|沒有記錄|没有記錄|沒有紀錄|---+|-|n\/?a|nil)\s*\)?$/i;
export const isPlaceholder = (s: string | null | undefined) => !s || PLACEHOLDER.test(s.trim());

/** the two names of a sign, Chinese first, without placeholders or repeats */
export function signNames(s: { en: string | null; tc: string | null }) {
  const names = [s.tc, s.en].filter((n): n is string => !isPlaceholder(n));
  const uniq = names.filter((n, i) => names.findIndex((m) => m.toLowerCase() === n.toLowerCase()) === i);
  return uniq;
}

export const TYPE_LABEL: Record<string, string> = {
  RL: "General restaurant",
  RR: "Light refreshment",
  MR: "Marine restaurant",
};
