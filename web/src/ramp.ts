// One colour system for change frequency on badges, dots and the legend: green (no change)
// through yellow to red. Digits always carry the count, so colour is never the only cue.
export const STEPS = [
  { fill: "#3FBF6F", ink: "#06331A", label: "0" },
  { fill: "#B4D335", ink: "#2C3804", label: "1" },
  { fill: "#FFCE3A", ink: "#4A3500", label: "2" },
  { fill: "#FF8A3A", ink: "#3F1500", label: "3" },
  { fill: "#D92D20", ink: "#FFFFFF", label: "4+" },
] as const;

export const stepOf = (n: number) => Math.min(Math.max(n, 0), 4);

// On the dark basemap the zero green is deepened so the shops that changed still lead.
export const ZERO_DARK = "#2E8C55";
export const zeroFill = (dark: boolean) => (dark ? ZERO_DARK : STEPS[0].fill);

// The heat wash ramp and its stops are written by pipeline/heat.py into meta.json,
// so the images and the legend always agree.
