export const YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026] as const;
export type Year = (typeof YEARS)[number];

/** Properties on each point in units.geojson (kept short; ~17k features). */
export interface UnitProps {
  id: number;
  en: string; // address, English
  tc: string; // address, Chinese
  s: string; // current or last sign
  chg: number; // store changes since 2016 (latest)
  /** one digit per year 2016..2026: cumulative store changes at year end (capped at 9) */
  c: string;
  /** one char per year: 0 not yet listed, 1 listed at year end, 2 listed before, none at year end */
  l: string;
  res: "r" | "b"; // resolved unit, or building level only
  t: "RL" | "RR" | "MR" | "";
  rr: 0 | 1; // only light refreshment licences ever
  seat: 0 | 1; // outside seating ever recorded
  sl: 0 | 1; // street level (ground floor)
  d: string; // FEHD district code
}

export interface SignSpan {
  en: string | null;
  tc: string | null;
  first_seen: string;
  last_seen: string;
}

export interface Licence {
  licno: string;
  first_seen: string;
  last_seen: string;
  expdate_last: string;
  lic_types: string[];
  endorsements: string[];
  gaps: { from: string; to: string }[];
  src: [string, string][];
}

export interface SignHistory {
  signs: SignSpan[];
  lic_types: string[];
  endorsements: string[];
  first_seen: string;
  last_seen: string;
  first_not_seen: string | null;
  listed_before_2016: boolean;
  listed_in_latest_snapshot: boolean;
  licences: Licence[];
  links: { from: string; to: string; rule: string; status: string }[];
  end: { label: string; status: string; months_early?: number } | null;
}

export interface UnitDetail {
  id: number;
  unit_id: string;
  address_en: string;
  address_tc: string | null;
  floors: string[];
  shops: string[];
  resolution: "resolved" | "building_only";
  lat: number;
  lon: number;
  store_changes: number;
  changes: { year: number; from: string; to: string; first_seen: string; possible_link: unknown }[];
  listed_now: boolean;
  current_listed_since: string | null;
  lic_types_ever: string[];
  outside_seating_ever: boolean;
  unlisted_gaps: { from: string; to: string; months: number }[];
  sign_histories: SignHistory[];
  first_file: string;
  latest_file: string;
}

export interface Meta {
  first_file: string;
  latest_file: string;
  files_good: number;
  files_quarantined: number;
  versions_in_archive: number;
  units: number;
  units_street_level: number;
  units_resolved: number;
  districts: string[];
  renewal_lag_months: number;
  heat: { bounds: [[number, number], [number, number], [number, number], [number, number]]; years: number[] };
  generated: string;
}

export type SearchRow = [id: number, en: string, tc: string, signs: string, chg: number, lon: number, lat: number];

export interface Filters {
  streetOnly: boolean;
  type: "all" | "RL" | "RR";
  seat: boolean;
  prevOnly: boolean;
  minChanges: number; // 0 = all
}

export const DEFAULT_FILTERS: Filters = { streetOnly: true, type: "all", seat: false, prevOnly: false, minChanges: 0 };
