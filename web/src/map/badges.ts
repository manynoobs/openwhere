import type { Map as MLMap } from "maplibre-gl";
import { STEPS, stepOf, zeroFill } from "../ramp";

// Badges are drawn once on a canvas in the system font and registered as map images,
// so they render like native pins and need no glyph files.
const FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Rounded", "SF Pro Text", "Helvetica Neue", "PingFang HK", sans-serif';
export const BADGE_LABELS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];
export type BadgeState = "f" | "h" | "d"; // filled · hollow (none listed now) · building level only

export const badgeName = (label: string, state: BadgeState) => `b-${label}-${state}`;

/** pins point at the shopfront with their tip */
export const MARKER_ANCHOR = "bottom";

type Step = { fill: string; ink: string };

function canvas(w: number, h: number, pr: number) {
  const c = document.createElement("canvas");
  c.width = Math.ceil(w * pr);
  c.height = Math.ceil(h * pr);
  const g = c.getContext("2d")!;
  g.scale(pr, pr);
  return { c, g };
}

function shade(hex: string, amt: number) {
  const n = parseInt(hex.slice(1), 16);
  const f = (v: number) => Math.max(0, Math.min(255, Math.round(v + (amt > 0 ? (255 - v) * amt : v * amt))));
  return `rgb(${f(n >> 16)}, ${f((n >> 8) & 255)}, ${f(n & 255)})`;
}

function digit(g: CanvasRenderingContext2D, label: string, x: number, y: number, size: number, color: string) {
  g.fillStyle = color;
  g.font = `700 ${label.length > 1 ? size - 2 : size}px ${FONT}`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(label, x, y + 0.7);
}

function softShadow(g: CanvasRenderingContext2D, blur = 4, y = 1.5, a = 0.26) {
  g.shadowColor = `rgba(16, 20, 30, ${a})`;
  g.shadowBlur = blur;
  g.shadowOffsetY = y;
}

function dashedRing(g: CanvasRenderingContext2D, x: number, y: number, r: number, color: string) {
  g.save();
  g.beginPath();
  g.arc(x, y, r, 0, Math.PI * 2);
  g.setLineDash([2.4, 2.2]);
  g.lineWidth = 1.3;
  g.strokeStyle = color;
  g.globalAlpha = 0.6;
  g.stroke();
  g.restore();
}

/** Apple Maps–style pin: the tip marks the shopfront, the head carries the count */
function pin(label: string, state: BadgeState, s: Step, pr: number) {
  const d = 24, pad = 4, tail = 7;
  const W = d + pad * 2, H = d + tail + pad * 2;
  const { c, g } = canvas(W, H, pr);
  const x = W / 2, y = pad + d / 2, r = d / 2;
  const tipY = pad + d + tail - 1;
  const a0 = Math.PI * 0.72;
  const path = () => {
    g.beginPath();
    g.arc(x, y, r, a0, Math.PI * 2.28);
    g.quadraticCurveTo(x + 3, y + r + 2, x, tipY);
    g.quadraticCurveTo(x - 3, y + r + 2, x + r * Math.cos(a0), y + r * Math.sin(a0));
    g.closePath();
  };
  g.save();
  softShadow(g, 4, 2, 0.3);
  path();
  g.fillStyle = "#FFFFFF";
  g.fill();
  g.restore();
  g.save();
  g.translate(x, y);
  g.scale((r - 2) / r, (r - 2) / r);
  g.translate(-x, -y);
  path();
  if (state === "h") {
    g.fillStyle = "#FFFFFF";
    g.fill();
    g.lineWidth = 2.6;
    g.strokeStyle = s.fill;
    g.stroke();
  } else {
    const grad = g.createLinearGradient(0, y - r, 0, tipY);
    grad.addColorStop(0, shade(s.fill, 0.14));
    grad.addColorStop(1, shade(s.fill, -0.1));
    g.fillStyle = grad;
    g.fill();
  }
  g.restore();
  if (state === "d") dashedRing(g, x, y, r - 4.4, s.ink);
  digit(g, label, x, y, 13, state === "h" ? "#1D1F24" : s.ink);
  return g.getImageData(0, 0, c.width, c.height);
}

export function registerBadges(map: MLMap, dark: boolean) {
  const pr = Math.max(2, Math.ceil(window.devicePixelRatio || 1));
  for (const label of BADGE_LABELS) {
    const base = STEPS[stepOf(Number(label))];
    const step = label === "0" ? { ...base, fill: zeroFill(dark) } : base;
    for (const state of ["f", "h", "d"] as BadgeState[]) {
      const name = badgeName(label, state);
      if (!map.hasImage(name)) map.addImage(name, pin(label, state, step, pr), { pixelRatio: pr });
    }
  }
}
