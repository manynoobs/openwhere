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

// Continuous ramp for the heat wash, in changes per shop since 2016.
// Stops are mirrored in pipeline/heat.py so the image and the legend agree.
export const HEAT_STOPS: [number, string][] = [
  [0.0, "#9ADBD3"],
  [0.25, "#FFD36A"],
  [0.5, "#FF9A45"],
  [0.8, "#E5372B"],
  [1.2, "#8E1B3A"],
];
