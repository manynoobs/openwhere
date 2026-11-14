import { PinMark } from "./PinMark";
import { YEARS } from "../types";
import { Icon } from "./Icon";

export function Legend({ heat, stops, district, year }: { heat: boolean; stops: [number, string][] | null; district?: number; year: number }) {
  if (heat && stops) {
    // the surface holds the share still listed after three years; the legend reads it as turnover,
    // so it runs green (few new shops gone) to red (many gone), the same way as the pins
    const turnover = [...stops].reverse().map(([v, c]) => [1 - v, c] as const);
    const lo = turnover[0][0];
    const hi = turnover[turnover.length - 1][0];
    const grad = `linear-gradient(90deg, ${turnover.map(([v, c]) => `${c} ${((v - lo) / (hi - lo)) * 100}%`).join(", ")})`;
    return (
      <div className="legend glass" aria-live="polite">
        <div className="cap">New shops no longer listed within 3 years</div>
        <div className="gradient" style={{ background: grad }} />
        <div className="gticks num">
          <span>{Math.round(lo * 100)}% low</span>
          {district != null && <span>{Math.round((1 - district) * 100)}% average</span>}
          <span>{Math.round(hi * 100)}% high</span>
        </div>
        <div className="key">
          <span>Paler colour = fewer shops to go on</span>
        </div>
      </div>
    );
  }
  return (
    <div className="legend glass" aria-live="polite">
      <div className="cap">Store changes {year < YEARS[YEARS.length - 1] ? `2016–${year}` : "since 2016"}</div>
      <div className="row legend-pins">
        {[0, 1, 2, 3, 4].map((n) => (
          <PinMark key={n} n={n} size={22} label={n === 4 ? "4+" : undefined} />
        ))}
      </div>
      <div className="key">
        <span><PinMark n={2} size={15} hollow label="" />White pin: no licence listed now</span>
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
