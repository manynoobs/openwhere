import type { Map as MLMap } from "maplibre-gl";
import { STEPS, stepOf } from "../ramp";

// Badges are drawn once on a canvas in the system font and registered as map images,
// so they render like native pins and need no glyph files.
const FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "PingFang HK", sans-serif';
export const BADGE_LABELS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
export type BadgeState = "f" | "h" | "d"; // filled · hollow (none listed now) · building level only

export const badgeName = (label: string, state: BadgeState) => `b-${label}-${state}`;

function draw(label: string, state: BadgeState, pr: number) {
  const step = STEPS[stepOf(Number(label))];
  const h = 22;
  const w = 22;
  const pad = 3; // room for the soft shadow
  const c = document.createElement("canvas");
  c.width = (w + pad * 2) * pr;
  c.height = (h + pad * 2 + 1) * pr;
  const g = c.getContext("2d")!;
  g.scale(pr, pr);
  const cx = pad + w / 2;
  const cy = pad + h / 2;
  const r = h / 2;

  g.save();
  g.shadowColor = "rgba(20, 20, 30, 0.28)";
  g.shadowBlur = 3;
  g.shadowOffsetY = 1;
  g.beginPath();
  g.arc(cx, cy, r, 0, Math.PI * 2);
  g.fillStyle = state === "h" ? "#FFFFFF" : step.fill;
  g.fill();
  g.restore();

  // white keyline so badges separate from each other and from the basemap
  g.beginPath();
  g.arc(cx, cy, r - 0.75, 0, Math.PI * 2);
  g.lineWidth = 1.5;
  g.strokeStyle = "#FFFFFF";
  g.stroke();

  if (state === "h") {
    g.beginPath();
    g.arc(cx, cy, r - 3, 0, Math.PI * 2);
    g.lineWidth = 2.5;
    g.strokeStyle = step.fill === "#DADDE3" ? "#9EA3AD" : step.fill;
    g.stroke();
  }
  if (state === "d") {
    g.beginPath();
    g.arc(cx, cy, r - 2.6, 0, Math.PI * 2);
    g.setLineDash([2.2, 2]);
    g.lineWidth = 1.2;
    g.strokeStyle = step.ink;
    g.globalAlpha = 0.55;
    g.stroke();
    g.globalAlpha = 1;
  }

  // zero carries no digit: a calm grey dot, so the shops that changed read first
  if (label === "0") return g.getImageData(0, 0, c.width, c.height);
  g.fillStyle = state === "h" ? "#1D1F24" : step.ink;
  g.font = `700 ${label.length > 1 ? 10.5 : 12.5}px ${FONT}`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(label, cx, cy + 0.6);
  return g.getImageData(0, 0, c.width, c.height);
}

export function registerBadges(map: MLMap) {
  const pr = Math.max(2, Math.ceil(window.devicePixelRatio || 1));
  for (const label of BADGE_LABELS) {
    for (const state of ["f", "h", "d"] as BadgeState[]) {
      const name = badgeName(label, state);
      if (!map.hasImage(name)) map.addImage(name, draw(label, state, pr), { pixelRatio: pr });
    }
  }
}
