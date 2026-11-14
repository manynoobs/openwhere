import { Fragment, useEffect, useState } from "react";
import { isPlaceholder, loadUnit, monthYear, signNames, TYPE_LABEL, yearOf } from "../data";
import type { SignHistory, UnitDetail, UnitProps } from "../types";
import { Chip } from "./Chip";
import { STEPS, stepOf } from "../ramp";
import { Icon } from "./Icon";
import { titleCase } from "./Search";

interface Props {
  id: number | null;
  props: UnitProps | null;
  pinned: boolean;
  canPin: boolean;
  onPin: () => void;
  onClose: () => void;
}

export function UnitPanel({ id, props, pinned, canPin, onPin, onClose }: Props) {
  const [unit, setUnit] = useState<UnitDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id == null) return;
    let live = true;
    setError(null);
    loadUnit(id)
      .then((u) => live && setUnit(u))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && id != null && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [id, onClose]);

  const open = id != null;
  const u = unit && unit.id === id ? unit : null;

  return (
    <aside className={`panel glass ${open ? "open" : ""}`} aria-hidden={!open} aria-label="Shopfront history">
      {props && (
        <div className="panel-head">
          <div className="top">
            <h2>{titleCase(props.en)}</h2>
            <button className="close" aria-label="Close" onClick={onClose}>
              <Icon name="close" size={16} />
            </button>
          </div>
          {props.tc && <div className="addr">{props.tc}</div>}
          <div className="figure">
            <Chip n={props.chg} className="big" />
            <div className="what">
              {props.chg === 1 ? "1 store change" : `${props.chg} store changes`} since 2016
              <small>{u ? statusLine(u) : " "}</small>
            </div>
          </div>
          {u && <Tags u={u} />}
          <div className="actions">
            <button className={`btn ${pinned ? "" : "primary"}`} onClick={onPin} disabled={!pinned && !canPin}>
              <Icon name="pin" size={16} />
              {pinned ? "Pinned to compare" : canPin ? "Pin to compare" : "Compare holds 3"}
            </button>
          </div>
        </div>
      )}
      <div className="panel-body">
        {error && <p className="loading">This shopfront’s history could not be loaded. {error}</p>}
        {!u && !error && open && <p className="loading">Loading history…</p>}
        {u && <History u={u} />}
      </div>
    </aside>
  );
}

function statusLine(u: UnitDetail) {
  const now = [...u.sign_histories].reverse().find((h) => h.listed_in_latest_snapshot);
  if (now) {
    const name = lastName(now);
    return `${name ? `${name} listed` : "Listed"} since ${now.listed_before_2016 ? "before 2016" : monthYear(now.first_seen)}`;
  }
  const last = u.sign_histories[u.sign_histories.length - 1];
  return `No restaurant licence listed now · last listed ${monthYear(last.last_seen)}`;
}

function lastName(h: SignHistory) {
  for (const s of [...h.signs].reverse()) {
    const n = signNames(s);
    if (n.length) return n[0];
  }
  return null;
}

function Tags({ u }: { u: UnitDetail }) {
  const tags: string[] = [];
  if (u.lic_types_ever.length === 1 && u.lic_types_ever[0] === "RR") tags.push("Only light refreshment licences recorded");
  else if (u.lic_types_ever.includes("RL")) tags.push("General restaurant licence recorded");
  if (u.outside_seating_ever) tags.push("Outside seating recorded");
  if ((u as UnitDetail & { shared?: boolean }).shared) tags.push("Several shops share this address");
  else if (u.resolution !== "resolved") tags.push("Located to the building, not the shop");
  return (
    <div className="tags">
      {tags.map((t) => (
        <span key={t} className="tag">{t}</span>
      ))}
    </div>
  );
}

const END_LABEL: Record<string, (h: SignHistory) => string> = {
  not_observed_before_recorded_expiry: (h) =>
    `Stopped being listed ${h.end?.months_early ?? ""} months before its licence’s recorded expiry`,
  not_observed_after_recorded_expiry: () => "Not listed after its licence’s recorded expiry",
  no_successor_identified: () => "Provisional licence; no full licence found after it",
  possible_successor_signs_differ: () => "Provisional licence; the next licence here is under a different sign, so we do not link them",
};

function History({ u }: { u: UnitDetail }) {
  const hs = [...u.sign_histories].reverse(); // newest first
  const changeYears = new Map(u.changes.map((c) => [c.first_seen, c]));
  const gapsByEnd = new Map(u.unlisted_gaps.map((g) => [g.to, g]));
  return (
    <>
      <h3>Signs at this address</h3>
      <ul className="timeline">
        {hs.map((h, i) => {
          const change = changeYears.get(h.first_seen);
          const gap = gapsByEnd.get(h.first_seen);
          return (
            <Fragment key={h.first_seen + i}>
              <HistoryRow h={h} />
              {change && (
                <li className="marker num">
                  <span className="dot" style={{ background: STEPS[stepOf(u.changes.indexOf(change) + 1)].fill }} />
                  Store change {u.changes.indexOf(change) + 1} of {u.changes.length} · {monthYear(change.first_seen)}
                  {change.possible_link ? " · signs differ, may be linked" : ""}
                </li>
              )}
              {gap && (
                <li className="marker gap num">
                  <span className="dot" />
                  No licence observed · {monthYear(gap.from)} – {monthYear(gap.to)} ({gap.months} months)
                </li>
              )}
            </Fragment>
          );
        })}
      </ul>

      <details className="records">
        <summary>
          Records behind this <Icon name="chevron" size={14} />
        </summary>
        <div className="rtable-wrap">
          <table className="rtable num">
            <thead>
              <tr>
                <th>Licence no.</th>
                <th>First listed</th>
                <th>Last listed</th>
                <th>Recorded expiry</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {u.sign_histories.flatMap((h) =>
                h.licences.map((l) => (
                  <tr key={l.licno}>
                    <td>{l.licno}</td>
                    <td>{monthYear(l.first_seen)}</td>
                    <td>{monthYear(l.last_seen)}</td>
                    <td>{l.expdate_last ? monthYear(l.expdate_last) : "–"}</td>
                    <td>{l.lic_types.join(", ")}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
        <p className="fine">
          Source: FEHD restaurant licence lists (English and Chinese), monthly archived files {monthYear(u.first_file)} –{" "}
          {monthYear(u.latest_file)}. A link between licence numbers is made only by a stated rule. Not a record of ownership,
          tenancy or business performance.
        </p>
      </details>
    </>
  );
}

function HistoryRow({ h }: { h: SignHistory }) {
  const names = h.signs.map(signNames).filter((n) => n.length);
  const main = names[names.length - 1] ?? [];
  const ended = !h.listed_in_latest_snapshot;
  const renamed = names.length > 1 && h.licences.length >= 1;
  const linked = h.links.filter((l) => l.status === "inferred").length;
  const types = h.lic_types.map((t) => TYPE_LABEL[t] ?? t).join(" · ");
  return (
    <li>
      <div className="t-years num">
        {h.listed_before_2016 ? "≤2015" : yearOf(h.first_seen)}–{ended ? yearOf(h.last_seen) : "now"}
        <small>{h.listed_before_2016 ? "before 2016" : monthYear(h.first_seen)}</small>
      </div>
      <div>
        <div className={`t-sign ${ended ? "ended" : ""}`}>
          {main[0] ?? "Sign not recorded"}
          {!ended && <span className="t-now">Listed now</span>}
          {main[1] && <span className="en">{main[1]}</span>}
        </div>
        <div className="t-meta">
          {types}
          {h.endorsements.includes("#A") ? " · Outside seating" : ""}
        </div>
        {renamed && (
          <div className="t-note">
            Sign changed under the same licence: {names.slice(0, -1).map((n) => n[0]).join(" → ")} → {main[0]}
          </div>
        )}
        {linked > 0 && (
          <div className="t-note">
            {linked === 1 ? "A provisional and a full licence" : `${linked + 1} licences`} under this sign, counted as one shop
          </div>
        )}
        {h.links.some((l) => l.rule === "prov_then_full_no_sign") && (
          <div className="t-note">First licence had no sign recorded; linked to the next one at this address</div>
        )}
        {h.end && END_LABEL[h.end.label] && <div className="t-note">{END_LABEL[h.end.label](h)}</div>}
        {h.signs.every((s) => isPlaceholder(s.en) && isPlaceholder(s.tc)) && (
          <div className="t-note">The licence list gives no sign for this licence</div>
        )}
      </div>
    </li>
  );
}
