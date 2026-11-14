import { useEffect, useState } from "react";
import { loadUnit, monthYear, signNames, TYPE_LABEL } from "../data";
import { YEARS, type UnitDetail } from "../types";
import { Chip } from "./Chip";
import { Icon } from "./Icon";
import { shortAddress } from "./Search";

const T0 = Date.UTC(2016, 0, 1);
const T1 = Date.UTC(2027, 0, 1);
const pos = (iso: string) => ((Date.parse(iso) - T0) / (T1 - T0)) * 100;

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

const nameOf = (s: { en: string | null; tc: string | null }[]) => {
  for (const x of [...s].reverse()) {
    const n = signNames(x);
    if (n.length) return n[0];
  }
  return "Sign not recorded";
};

interface Props {
  ids: number[];
  onClose: () => void;
  onUnpin: (id: number) => void;
  onOpen: (u: UnitDetail) => void;
}

export function CompareSheet({ ids, onClose, onUnpin, onOpen }: Props) {
  const units = usePinned(ids);
  return (
    <section className="sheet glass" aria-label="Compare pinned shopfronts">
      <div className="sheet-head">
        <h2>Compare {ids.length} shopfronts</h2>
        <button className="btn" onClick={() => window.print()}>
          <Icon name="print" size={16} />
          Print
        </button>
        <button className="close" aria-label="Close compare" onClick={onClose}>
          <Icon name="close" size={16} />
        </button>
      </div>
      <div className="sheet-body">
        <div className="axis">
          <span />
          <div className="years num">
            {YEARS.map((y) => (
              <span key={y}>{y}</span>
            ))}
          </div>
        </div>
        {units.map((u) => (
          <div className="crow" key={u.id}>
            <div className="who">
              <Chip n={u.store_changes} />
              <button className="linkbtn" style={{ minWidth: 0, textAlign: "left", color: "inherit" }} onClick={() => onOpen(u)}>
                <b>{shortAddress(u.address_en)}</b>
                <small>{u.store_changes === 1 ? "1 store change" : `${u.store_changes} store changes`}</small>
              </button>
              <button className="unpin" aria-label="Unpin" onClick={() => onUnpin(u.id)}>
                <Icon name="x" size={14} />
              </button>
            </div>
            <div className="track">
              {u.sign_histories.map((h, i) => {
                const a = Math.max(0, pos(h.first_seen));
                const b = Math.min(100, pos(h.last_seen) + 100 / 132);
                return (
                  <span key={i} className="bar" title={`${nameOf(h.signs)} · ${monthYear(h.first_seen)} – ${monthYear(h.last_seen)}`}
                    style={{ left: `${a}%`, width: `${Math.max(b - a, 0.8)}%`, top: i % 2 ? 5 : 5 }}>
                    {nameOf(h.signs)}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/** What the browser prints: the pinned units, each fact with its source line. */
export function PrintSheet({ ids }: { ids: number[] }) {
  const units = usePinned(ids);
  if (!units.length) return null;
  return (
    <div className="print-only">
      <h1>Shopfront Past Lives · 鋪位前世 — comparison</h1>
      {units.map((u) => (
        <section key={u.id}>
          <h2>
            {shortAddress(u.address_en)} {u.address_tc ? `· ${u.address_tc}` : ""} — {u.store_changes} store change
            {u.store_changes === 1 ? "" : "s"} since 2016
          </h2>
          <table>
            <thead>
              <tr>
                <th>Sign</th>
                <th>Listed</th>
                <th>Licence type</th>
                <th>Source (licence no., first and last file)</th>
              </tr>
            </thead>
            <tbody>
              {u.sign_histories.map((h, i) => (
                <tr key={i}>
                  <td>{h.signs.map(signNames).filter((n) => n.length).map((n) => n.join(" / ")).join(" → ") || "Sign not recorded"}</td>
                  <td>
                    {h.listed_before_2016 ? "before 2016" : monthYear(h.first_seen)} – {h.listed_in_latest_snapshot ? "now" : monthYear(h.last_seen)}
                  </td>
                  <td>{h.lic_types.map((t) => TYPE_LABEL[t] ?? t).join(", ")}</td>
                  <td>
                    {h.licences.map((l) => `${l.licno} (${l.src[0][0].slice(0, 8)}–${l.src[l.src.length - 1][1].slice(0, 8)})`).join("; ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      <footer>
        Reconstructed from FEHD restaurant licence lists, monthly archived files via DATA.GOV.HK. Not a record of ownership,
        tenancy or business performance.
      </footer>
    </div>
  );
}
