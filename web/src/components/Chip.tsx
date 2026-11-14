import { STEPS, stepOf } from "../ramp";

/** The change count as it appears on the map: same colour, same digit. */
export function Chip({ n, hollow = false, className = "" }: { n: number; hollow?: boolean; className?: string }) {
  const s = STEPS[stepOf(n)];
  const style = hollow
    ? { color: stepOf(n) === 0 ? "#8a8f99" : s.fill }
    : { background: s.fill, color: s.ink };
  return (
    <span className={`chip num ${hollow ? "hollow" : ""} ${className}`} style={style}>
      <span style={hollow ? { color: "#1d1f24" } : undefined}>{n}</span>
    </span>
  );
}
