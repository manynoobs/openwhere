import { useEffect, useState } from "react";
import { isPlaceholder, loadUnit, monthYear, signNames, TYPE_LABEL, yearOf } from "../data";
import { CUISINE_LABEL, type SignHistory, type UnitDetail, type UnitProps } from "../types";
import { Icon } from "./Icon";
import { PinMark } from "./PinMark";
import { shortAddress } from "./Search";

interface Props {
  id: number | null;
  props: UnitProps | null;
  pinned: boolean;
  canPin: boolean;
  priceBands: string[];
  onPin: () => void;
  onClose: () => void;
  onCheck: (u: UnitProps) => void;
}

export function UnitPanel({ id, props, pinned, canPin, priceBands, onPin, onClose, onCheck }: Props) {
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
  const now = u ? [...u.sign_histories].reverse().find((h) => h.listed_in_latest_snapshot) ?? null : null;
  const listedNow = props ? props.l[props.l.length - 1] === "1" : false;

  return (
    <aside className={`panel glass ${open ? "open" : ""}`} aria-hidden={!open} aria-label="Shopfront" {...(open ? {} : { inert: "" })}>
      {props && (
        <div className="panel-head">
          <div className="top">
            <div className="who">
              <h2>{listedNow ? props.s || "Sign not recorded" : "No restaurant licence now"}</h2>
              {listedNow && <Cuisine u={u} props={props} />}
            </div>
            <button className="close" aria-label="Close" onClick={onClose}>
              <Icon name="close" size={16} />
            </button>
          </div>
          <div className="addr">
            {shortAddress(props.en)}
            {props.tc && <span>{props.tc}</span>}
          </div>

          <dl className="keyfacts num">
            <div>
              <dt>Price per person</dt>
              <dd>{listedNow ? props.pr >= 0 ? priceBands[props.pr] : <span className="nodata">No data</span> : "–"}</dd>
            </div>
            <div>
              <dt>Store changes since 2016</dt>
              <dd className="with-pin">
                <PinMark n={props.chg} size={16} hollow={!listedNow} />
                {props.chg}
              </dd>
            </div>
            <div>
              <dt>{listedNow ? "This shop here since" : "Last licence listed"}</dt>
              <dd>{u ? (now ? (now.listed_before_2016 ? "before 2016" : monthYear(now.first_seen)) : lastListed(u)) : "…"}</dd>
            </div>
            <div>
              <dt>Nearest MTR exit</dt>
              <dd>
                {props.mtr} m <small>{props.mtrx}</small>
              </dd>
            </div>
            <div className="wide">
              <dt>Kitchen</dt>
              <dd>{kitchen(u, props)}</dd>
            </div>
          </dl>

          <div className="actions">
            <button className="btn primary" onClick={() => onCheck(props)}>
              <Icon name="target" size={16} />
              Check this spot
            </button>
            <button className="btn" onClick={onPin} disabled={!pinned && !canPin}>
              <Icon name="pin" size={16} />
              {pinned ? "Pinned" : canPin ? "Pin to compare" : "Compare holds 3"}
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

function Cuisine({ u, props }: { u: UnitDetail | null; props: UnitProps }) {
  const or = u?.openrice;
  if (or) return <p className="cuisine">{or.cuisines.join(" · ")}</p>;
  if (props.cu && props.cu !== "unknown")
    return (
      <p className="cuisine">
        {CUISINE_LABEL[props.cu]} <small>guessed from the name</small>
      </p>
    );
  return null;
}

function lastListed(u: UnitDetail) {
  const last = u.sign_histories[u.sign_histories.length - 1];
  return monthYear(last.last_seen);
}

/** what a would-be tenant needs from the licence type: can they run a full kitchen here */
function kitchen(u: UnitDetail | null, props: UnitProps) {
  const types = u?.lic_types_ever ?? [props.t];
  if (types.includes("RL")) return "Full kitchen on record (general restaurant licence)";
  if (types.includes("RR")) return "Light refreshment only, no general licence on record";
  return TYPE_LABEL[props.t] ?? "–";
}

function nameOf(h: SignHistory) {
  for (const s of [...h.signs].reverse()) {
    const n = signNames(s);
    if (n.length) return n;
  }
  return [];
}

function History({ u }: { u: UnitDetail }) {
  const hs = [...u.sign_histories].reverse(); // newest first
  const gapsByEnd = new Map(u.unlisted_gaps.map((g) => [g.to, g]));
  return (
    <>
      <h3>Shops at this address</h3>
      <ol className="shops">
        {hs.map((h, i) => {
          const names = nameOf(h);
          const ended = !h.listed_in_latest_snapshot;
          const gap = gapsByEnd.get(h.first_seen);
          return (
            <li key={h.first_seen + i} className={ended ? "ended" : "now"}>
              <span className="yrs num">
                {h.listed_before_2016 ? "≤2016" : yearOf(h.first_seen)}–{ended ? yearOf(h.last_seen) : "now"}
              </span>
              <span className="nm">
                {names[0] ?? "Sign not recorded"}
                {names[1] && <small>{names[1]}</small>}
              </span>
              {gap && <span className="gapnote num">after {gap.months} months with no licence</span>}
            </li>
          );
        })}
      </ol>

      <details className="records">
        <summary>
          Records behind this <Icon name="chevron" size={14} />
        </summary>
        <ul className="record-notes">
          {hs.map((h, i) => (
            <RecordNotes key={i} h={h} />
          ))}
        </ul>
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
          Source: FEHD restaurant licence lists (English and Chinese), monthly files {monthYear(u.first_file)} –{" "}
          {monthYear(u.latest_file)}. Price and cuisine from OpenRice where a listing matched this shop. Not a record of ownership,
          tenancy or business performance.
        </p>
      </details>
    </>
  );
}

const END_LABEL: Record<string, (h: SignHistory) => string> = {
  not_observed_before_recorded_expiry: (h) => `stopped being listed ${h.end?.months_early ?? ""} months before its licence expired`,
  not_observed_after_recorded_expiry: () => "not listed after its licence expired",
};

function RecordNotes({ h }: { h: SignHistory }) {
  const names = h.signs.map(signNames).filter((n) => n.length);
  const notes: string[] = [];
  if (names.length > 1) notes.push(`sign changed under the same licence (${names.map((n) => n[0]).join(" → ")})`);
  if (h.end && END_LABEL[h.end.label]) notes.push(END_LABEL[h.end.label](h));
  if (h.signs.every((s) => isPlaceholder(s.en) && isPlaceholder(s.tc))) notes.push("no sign given in the licence list");
  const types = h.lic_types.map((t) => TYPE_LABEL[t] ?? t).join(", ");
  return (
    <li>
      <b>{names[names.length - 1]?.[0] ?? "Sign not recorded"}</b>: {types}
      {notes.length > 0 && `; ${notes.join("; ")}`}
    </li>
  );
}
