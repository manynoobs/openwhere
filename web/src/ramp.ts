// One colour system for change frequency, shared by badges, dots, legend and the heat wash.
// Steps are 0, 1, 2, 3, 4+. Digits always carry the count, so colour is never the only cue.
export const STEPS = [
  { fill: "#DADDE3", ink: "#2B2F36", label: "0" },
  { fill: "#5CC6BA", ink: "#063A34", label: "1" },
  { fill: "#FFC53D", ink: "#4A3200", label: "2" },
  { fill: "#FF8A3D", ink: "#3F1500", label: "3" },
  { fill: "#E5372B", ink: "#FFFFFF", label: "4+" },
] as const;

export const stepOf = (n: number) => Math.min(Math.max(n, 0), 4);

// On the dark basemap a light grey zero would be the brightest thing on screen; it recedes instead.
export const ZERO_DARK = "#5E626B";
export const zeroFill = (dark: boolean) => (dark ? ZERO_DARK : STEPS[0].fill);

// The heat wash ramp and its stops are written by pipeline/heat.py into meta.json,
// so the images and the legend always agree.
