import { useEffect, useState } from "react";
import { loadUnit, monthYear, signNames } from "../data";
import { STEPS, stepOf } from "../ramp";
import { YEARS, type SignHistory, type UnitDetail } from "../types";
import { Icon } from "./Icon";
import { PinMark } from "./PinMark";
import { shortAddress } from "./Search";

const T0 = Date.UTC(2016, 0, 1);
const T1 = Date.UTC(2027, 0, 1);
const MONTH = 1 / 132; // one month as a share of the 2016-2026 axis
const pos = (iso: string) => Math.min(1, Math.max(0, (Date.parse(iso) - T0) / (T1 - T0)));

function usePinned(ids: number[]) {
  const [units, setUnits] = useState<UnitDetail[]>([]);
  useEffect(() => {
    let live = true;
    Promise.all(ids.map(loadUnit)).then((u) => live && setUnits(u));
    return () => {
      live = false;
    };
  }, [ids]);
  return units;
}

const nameOf = (h: SignHistory) => {
  for (const x of [...h.signs].reverse()) {
    const n = signNames(x);
    if (n.length) return n[0];
  }
  return "Sign not recorded";
};

const years = (a: string, b: string) => (Date.parse(b) - Date.parse(a)) / (365.25 * 864e5);

/** "G/F, 100 Portland Street, Yau Ma Tei" -> ["100 Portland Street", "G/F · Yau Ma Tei"] */
function addressLines(en: string) {
  const parts = shortAddress(en).split(/,\s*/);
  const street = parts.findIndex((p) => /^\d/.test(p) || /street|road|avenue|lane|terrace/i.test(p));
  if (street < 0) return [parts[0], parts.slice(1).join(" · ")];
  return [parts[street], [...parts.slice(0, street), ...parts.slice(street + 1)].join(" · ")];
}

/** what the map knows about a pinned shopfront's surroundings, worked out in App */
export interface CompareFacts {
  price: string | null;
  listed: boolean;
  mtr: number;
  mtrx: string;
  life: number | null; // share of new shops nearby still listed after three years
  cuisine: string; // label, "" when unknown
  rivals: number; // shops listed now within 200 m, of the same cuisine where known
}

interface Props {
  ids: number[];
  facts: Record<number, CompareFacts>;
  onClose: () => void;
  onUnpin: (id: number) => void;
  onOpen: (u: UnitDetail) => void;
}

export function CompareSheet({ ids, facts, onClose, onUnpin, onOpen }: Props) {
  const units = usePinned(ids);
  const empty = Math.max(0, 3 - ids.length);
  return (
    <section className="sheet glass" aria-label="Compare pinned shopfronts">
      <header className="sheet-head">
        <h2>Compare</h2>
        <span className="sheet-count num">{ids.length} of 3 pinned</span>
        <span className="sheet-spacer" />
        <button className="close" aria-label="Close compare" onClick={onClose}>
          <Icon name="close" size={16} />
        </button>
      </header>
      <div className="sheet-body">
        <div className="cmp-axis num" aria-hidden="true">
          <span />
          <div className="cmp-years">
            {YEARS.map((y) => (
              <span key={y}>{y === 2016 || y === 2026 || y % 2 === 0 ? `’${String(y).slice(2)}` : ""}</span>
            ))}
          </div>
        </div>
        {units.map((u) => (
          <Lane key={u.id} u={u} f={facts[u.id]} onOpen={() => onOpen(u)} onUnpin={() => onUnpin(u.id)} />
        ))}
        {Array.from({ length: empty }, (_, i) => (
          <div className="cmp-lane cmp-empty" key={`e${i}`}>
            <span className="cmp-empty-pin" />
            <span>Pin another shopfront from its history panel to compare it here</span>
          </div>
        ))}
      </div>
    </section>
  );
}

const rivalsWord = (f: CompareFacts) => `${f.cuisine ? `${f.cuisine} ` : ""}${f.rivals === 1 ? "shop" : "shops"} within 200 m`;

function Lane({ u, f, onOpen, onUnpin }: { u: UnitDetail; f?: CompareFacts; onOpen: () => void; onUnpin: () => void }) {
  const hs = u.sign_histories;
  const now = hs.find((h) => h.listed_in_latest_snapshot);
  const [line1, line2] = addressLines(u.address_en);
  const longest = Math.max(...hs.map((h) => years(h.first_seen, h.last_seen)));
  const gapMonths = u.unlisted_gaps.reduce((a, g) => a + g.months, 0);
  const changeAt = new Map(u.changes.map((c, i) => [c.first_seen, i + 1]));

  // sign labels sit under the bands on two staggered lines, each as wide as the room to the next
  const starts = hs.map((h) => pos(h.listed_before_2016 ? "2016-01-01" : h.first_seen));
  const labels = hs.map((h, i) => {
    const row = i % 2;
    const next = starts.findIndex((_, j) => j > i && j % 2 === row);
    const room = (next >= 0 ? starts[next] : 1) - starts[i];
    return { row, left: starts[i], room, name: nameOf(h) };
  });

  return (
    <div className="cmp-lane">
      <div className="cmp-who">
        <PinMark n={u.store_changes} size={26} />
        <button className="cmp-addr" onClick={onOpen} title="Open history">
          <b>{line1}</b>
          <small>{line2}</small>
        </button>
        <button className="unpin" aria-label="Unpin" onClick={onUnpin}>
          <Icon name="x" size={14} />
        </button>
      </div>
      <div className="cmp-time">
        <div className="cmp-track">
          {u.unlisted_gaps.map((g) => (
            <span key={g.from} className="cmp-gap" style={{ left: `${pos(g.from) * 100}%`, width: `${(pos(g.to) - pos(g.from)) * 100}%` }} />
          ))}
          {hs.map((h, i) => {
            const a = starts[i];
            const b = Math.max(pos(h.last_seen) + MONTH, a + MONTH);
            return (
              <span
                key={i}
                className={`cmp-band ${h.listed_in_latest_snapshot ? "now" : ""}`}
                style={{ left: `calc(${a * 100}% + 1.5px)`, width: `calc(${(b - a) * 100}% - 3px)` }}
                title={`${nameOf(h)} · ${h.listed_before_2016 ? "before 2016" : monthYear(h.first_seen)} – ${
                  h.listed_in_latest_snapshot ? "now" : monthYear(h.last_seen)
                }`}
              />
            );
          })}
          {hs.map((h, i) => {
            const k = changeAt.get(h.first_seen);
            if (!k) return null;
            return (
              <span
                key={`c${i}`}
                className="cmp-change"
                style={{ left: `${starts[i] * 100}%`, background: STEPS[stepOf(k)].fill }}
                title={`Store change ${k} · ${monthYear(h.first_seen)}`}
              />
            );
          })}
        </div>
        <div className="cmp-labels">
          {labels.map((l, i) => (
            <span
              key={i}
              className={`cmp-label row${l.row} ${hs[i].listed_in_latest_snapshot ? "now" : ""} ${l.left > 0.78 ? "end" : ""}`}
              // labels near the right edge hang from the end of the axis so they are not cut off
              style={
                l.left > 0.78
                  ? { right: 0, maxWidth: `calc(${(1 - (labels[i - 2]?.left ?? 0)) * 100}% - 6px)` }
                  : { left: `${l.left * 100}%`, maxWidth: `calc(${l.room * 100}% - 6px)` }
              }
              title={l.name}
            >
              {l.name}
            </span>
          ))}
        </div>
        <div className="cmp-facts num">
          <span>
            <b>{u.store_changes}</b> {u.store_changes === 1 ? "store change" : "store changes"}
          </span>
          <span>
            <b>{hs.length}</b> {hs.length === 1 ? "sign" : "signs"}
          </span>
          <span>
            Longest sign <b>{longest >= 1 ? `${longest.toFixed(1)} yrs` : `${Math.round(longest * 12)} mo`}</b>
          </span>
          {gapMonths > 0 && (
            <span>
              No licence <b>{gapMonths} mo</b>
            </span>
          )}
          <span className="cmp-now">{now ? `Now: ${nameOf(now)}` : "No licence listed now"}</span>
        </div>
        {f && (
          <div className="cmp-facts cmp-site num">
            {f.listed && (
              <span>
                Price per person <b>{f.price ?? "No data"}</b>
              </span>
            )}
            <span>
              MTR exit <b>{f.mtr} m</b>
            </span>
            {f.life != null && (
              <span>
                New shops nearby lasting 3 years <b>{Math.round(f.life * 100)}%</b>
              </span>
            )}
            <span>
              <b>{f.rivals}</b> {rivalsWord(f)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
