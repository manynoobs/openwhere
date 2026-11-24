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
  cu: string; // cuisine group for shops listed now (OpenRice where matched, else from the sign); "" otherwise
  pr: number; // OpenRice price band index into meta.price_bands; -1 = no data
  mtr: number; // straight-line metres to the nearest MTR exit
  mtrx: string; // that exit, e.g. "Yau Ma Tei Exit A1"
  lon?: number;
  lat?: number;
}

export const CUISINES: [key: string, label: string][] = [
  ["cha_chaan_teng", "Hong Kong style & cha chaan teng"],
  ["noodles", "Noodles & congee"],
  ["chinese", "Chinese"],
  ["japanese", "Japanese"],
  ["korean", "Korean"],
  ["se_asian", "Southeast Asian"],
  ["south_asian", "South Asian & Middle Eastern"],
  ["western", "Western"],
  ["fast_food", "Fast food & chains"],
  ["cafe", "Coffee, dessert & bakery"],
  ["hotpot_bbq", "Hot pot & barbecue"],
  ["bar", "Bar & nightlife"],
  ["hotel", "Hotel restaurant & banquet"],
];
export const CUISINE_LABEL: Record<string, string> = Object.fromEntries([...CUISINES, ["unknown", "Unclear from the name"]]);

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
  openrice: { price: string | null; cuisines: string[] } | null;
  rent?: UnitRent;
  first_file: string;
  latest_file: string;
}

/** median rents of Centaline leases or listings near a unit, on the same level */
export interface RentSummary {
  n: number;
  psf: number; // HK$ per square foot a month, median
  psf_low: number; // lower and upper quartile
  psf_high: number;
  area: number; // square feet, median
  rent: number; // HK$ a month, median
  radius: number; // metres searched
}

export interface UnitRent {
  level: "street" | "upstairs";
  since: string;
  leases: RentSummary | null;
  asking: RentSummary | null;
}

export interface RentMeta {
  kowloon_psf: number;
  kowloon_period: string;
  kowloon_provisional: boolean;
  since: string;
  listings_collected: string;
  units_with_leases: number;
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
  heat: {
    bounds: [[number, number], [number, number], [number, number], [number, number]];
    image: string;
    stops: [number, string][];
    district: number; // the district's own three-year share, the middle of the colour scale
    horizon_months: number;
    new_histories: number;
  };
  generated: string;
  price_bands: string[];
  openrice_matched: number;
  rent?: RentMeta;
}

export type SearchRow = [id: number, en: string, tc: string, signs: string, chg: number, lon: number, lat: number];

export interface Filters {
  streetOnly: boolean;
  type: "all" | "RL" | "RR";
  seat: boolean;
  prevOnly: boolean;
  minChanges: number; // 0 = all
  cuisine: string; // "" = any; applies to shops listed now
  price: number; // index into meta.price_bands; -1 = any
  brand: string; // part of a shop name, e.g. "McDonald's"; "" = any
  /** ids of the units whose sign matches `brand`, worked out once in App */
  brandIds?: number[] | null;
}

export const DEFAULT_FILTERS: Filters = {
  streetOnly: true, type: "all", seat: false, prevOnly: false, minChanges: 0, cuisine: "", price: -1, brand: "",
};

/** how many filters differ from the default, for the count on the Filters button */
export const activeFilters = (f: Filters) =>
  (f.streetOnly ? 0 : 1) + (f.type !== "all" ? 1 : 0) + (f.seat ? 1 : 0) + (f.prevOnly ? 1 : 0) + (f.minChanges ? 1 : 0) +
  (f.cuisine ? 1 : 0) + (f.price >= 0 ? 1 : 0) + (f.brand.trim() ? 1 : 0);

/** shop names compared without case, spaces or punctuation, so "mcdonalds" finds "McDonald’s" */
export const normName = (s: string) => s.toLowerCase().replace(/[\s,.'’()\-/·]+/g, "");
