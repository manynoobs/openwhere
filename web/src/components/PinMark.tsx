import { STEPS, stepOf } from "../ramp";

/** The map pin as an inline SVG: same shape, colour and digit as the markers on the map. */
export function PinMark({ n, size = 24, hollow = false, label }: { n: number; size?: number; hollow?: boolean; label?: string }) {
  const s = STEPS[stepOf(n)];
  const text = label ?? String(n);
  return (
    <svg className="pinmark" width={size} height={size * 1.3} viewBox="0 0 24 31" aria-hidden="true">
      <path
        d="M12 1.5a10.5 10.5 0 0 1 6.2 19c-2.3 1.7-4.6 4.5-6.2 8.5-1.6-4-3.9-6.8-6.2-8.5A10.5 10.5 0 0 1 12 1.5z"
        fill="#fff"
        style={{ filter: "drop-shadow(0 1px 1.5px rgba(16,20,30,.3))" }}
      />
      <path
        d="M12 3.3a8.7 8.7 0 0 1 5.1 15.7c-2 1.5-3.8 3.6-5.1 6.6-1.3-3-3.1-5.1-5.1-6.6A8.7 8.7 0 0 1 12 3.3z"
        fill={hollow ? "#fff" : s.fill}
        stroke={hollow ? s.fill : "none"}
        strokeWidth={hollow ? 2 : 0}
      />
      <text
        x="12"
        y="12.6"
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={text.length > 1 ? 8.5 : 10.5}
        fontWeight={700}
        fill={hollow ? "#1d1f24" : s.ink}
        fontFamily='-apple-system, BlinkMacSystemFont, "SF Pro Rounded", "SF Pro Text", sans-serif'
      >
        {text}
      </text>
    </svg>
  );
}
