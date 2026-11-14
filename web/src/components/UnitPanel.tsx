import { Fragment, useEffect, useState } from "react";
import { isPlaceholder, loadUnit, monthYear, signNames, TYPE_LABEL, yearOf } from "../data";
import { CUISINE_LABEL, type SignHistory, type UnitDetail, type UnitProps } from "../types";
import { PinMark } from "./PinMark";
import { STEPS, stepOf } from "../ramp";
import { Icon } from "./Icon";
import { shortAddress } from "./Search";

interface Props {
  id: number | null;
  props: UnitProps | null;
  pinned: boolean;
  canPin: boolean;
  onPin: () => void;
  onClose: () => void;
  onCheck: (u: UnitProps) => void;
}

export function UnitPanel({ id, props, pinned, canPin, onPin, onClose, onCheck }: Props) {
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
    <aside className={`panel glass ${open ? "open" : ""}`} aria-hidden={!open} aria-label="Shopfront history"
      {...(open ? {} : { inert: "" })}>
      {props && (
        <div className="panel-head">
          <div className="top">
            <h2>{shortAddress(props.en)}</h2>
            <button className="close" aria-label="Close" onClick={onClose}>
              <Icon name="close" size={16} />
            </button>
          </div>
          {props.tc && <div className="addr">{props.tc}</div>}
          <div className="figure">
            <PinMark n={props.chg} size={40} hollow={props.l[props.l.length - 1] === "2"} />
            <div className="what">
              {props.chg === 1 ? "1 store change" : `${props.chg} store changes`} since 2016
              <small>{u ? statusLine(u) : " "}</small>
            </div>
          </div>
          {u && <Tags u={u} />}
          <dl className="unit-facts">
            {props.cu && (
              <div>
                <dt>Cuisine</dt>
                <dd>
                  {CUISINE_LABEL[props.cu]}
                  {props.cu !== "unknown" && <small> · guessed from the name</small>}
                </dd>
              </div>
            )}
            <div>
              <dt>Nearest MTR exit</dt>
              <dd className="num">
                {props.mtr} m <small>· {props.mtrx}</small>
              </dd>
            </div>
          </dl>
          <div className="actions">
            <button className={`btn ${pinned ? "" : "primary"}`} onClick={onPin} disabled={!pinned && !canPin}>
              <Icon name="pin" size={16} />
              {pinned ? "Pinned to compare" : canPin ? "Pin to compare" : "Compare holds 3"}
            </button>
            <button className="btn" onClick={() => onCheck(props)}>
              <Icon name="target" size={16} />
              Check this spot
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
          {monthYear(u.latest_file)}. Not a record of ownership,
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
  const types = h.lic_types.map((t) => TYPE_LABEL[t] ?? t).join(" · ");
  return (
    <li>
      <div className="t-years num">
        {h.listed_before_2016 ? "2016" : yearOf(h.first_seen)}–{ended ? yearOf(h.last_seen) : "now"}
        <small>{h.listed_before_2016 ? "listed before 2016" : `from ${monthYear(h.first_seen)}`}</small>
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
            Sign changed: {names.slice(0, -1).map((n) => n[0]).join(" → ")} → {main[0]}
          </div>
        )}
        {h.end && END_LABEL[h.end.label] && <div className="t-note">{END_LABEL[h.end.label](h)}</div>}
        {h.signs.every((s) => isPlaceholder(s.en) && isPlaceholder(s.tc)) && (
          <div className="t-note">The licence list gives no sign for this licence</div>
        )}
      </div>
    </li>
  );
}
