import { STEPS } from "../ramp";
import { YEARS } from "../types";
import { Icon } from "./Icon";

export function Legend({ heat, stops, year }: { heat: boolean; stops: [number, string][] | null; year: number }) {
  if (heat && stops) {
    const lo = stops[0][0];
    const hi = stops[stops.length - 1][0];
    const grad = `linear-gradient(90deg, ${stops.map(([v, c]) => `${c} ${((v - lo) / (hi - lo)) * 100}%`).join(", ")})`;
    return (
      <div className="legend glass" aria-live="polite">
        <div className="cap">How often shops change here, 2016–{year}</div>
        <div className="gradient" style={{ background: grad }} />
        <div className="gticks">
          <span>Fewer changes</span>
          <span>More changes</span>
        </div>
      </div>
    );
  }
  return (
    <div className="legend glass" aria-live="polite">
      <div className="cap">Store changes since 2016</div>
      <div className="row">
        {STEPS.map((s) =>
          s.label === "0" ? (
            <span key="0" className="zero-key" title="No store change">
              <i style={{ background: s.fill }} />0
            </span>
          ) : (
            <span key={s.label} className="chip num" style={{ background: s.fill, color: s.ink }}>
              {s.label}
            </span>
          ),
        )}
      </div>
      <div className="key">
        <span><i className="swatch-hollow" />Hollow: no licence listed now</span>
        <span><i className="swatch-dash" />Shared address</span>
      </div>
    </div>
  );
}

interface YearProps {
  year: number;
  setYear: (y: number) => void;
  playing: boolean;
  setPlaying: (p: boolean) => void;
}

export function YearBar({ year, setYear, playing, setPlaying }: YearProps) {
  return (
    <div className="yearbar glass">
      <button className="play" aria-label={playing ? "Pause" : "Play the years from 2016"} onClick={() => setPlaying(!playing)}>
        <Icon name={playing ? "pause" : "play"} size={18} />
      </button>
      <div className="yr-label num" aria-live="polite">{year}</div>
      <div className="slider">
        <input
          type="range"
          min={YEARS[0]}
          max={YEARS[YEARS.length - 1]}
          step={1}
          value={year}
          aria-label="Show changes up to the end of year"
          onChange={(e) => {
            setPlaying(false);
            setYear(Number(e.target.value));
          }}
        />
        <div className="ticks num" aria-hidden="true">
          {YEARS.map((y) => (
            <span key={y}>{y % 2 === 0 ? `’${String(y).slice(2)}` : ""}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
