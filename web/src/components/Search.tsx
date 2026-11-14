import { useEffect, useMemo, useRef, useState } from "react";
import { loadSearch } from "../data";
import { normName, type SearchRow } from "../types";
import { PinMark } from "./PinMark";
import { Icon } from "./Icon";

const norm = normName;

interface Props {
  district: string;
  onPick: (row: SearchRow) => void;
}

export function Search({ district, onPick }: Props) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<SearchRow[] | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const keyed = useRef<{ row: SearchRow; key: string }[]>([]);

  const ensure = () => {
    if (rows) return;
    loadSearch().then((r) => {
      keyed.current = r.map((row) => ({ row, key: norm(`${row[1]} ${row[2]} ${row[3]}`) }));
      setRows(r);
    });
  };

  const results = useMemo(() => {
    const terms = q.trim().split(/\s+/).map(norm).filter(Boolean);
    if (!terms.length || !rows) return [];
    const hits = keyed.current.filter(({ key }) => terms.every((t) => key.includes(t)));
    // street-level and higher-change units first, then shorter addresses
    hits.sort((a, b) => b.row[4] - a.row[4] || a.row[1].length - b.row[1].length);
    return hits.slice(0, 8).map((h) => h.row);
  }, [q, rows]);

  useEffect(() => setActive(0), [q]);

  // "/" focuses search, as in most map apps
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT") {
        e.preventDefault();
        input.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const pick = (row: SearchRow) => {
    onPick(row);
    setOpen(false);
    input.current?.blur();
  };

  const showList = open && q.trim().length > 0;
  return (
    <div className="search" role="search">
      <div className="search-field">
        <Icon name="search" size={17} />
        <input
          ref={input}
          value={q}
          placeholder={`Search ${district} by address or shop name`}
          aria-label="Search by address or shop name, in English or Chinese"
          aria-expanded={showList}
          aria-controls="search-results"
          role="combobox"
          onFocus={() => {
            ensure();
            setOpen(true);
          }}
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, results.length - 1));
            else if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
            else if (e.key === "Enter" && results[active]) pick(results[active]);
            else if (e.key === "Escape") input.current?.blur();
            else return;
            e.preventDefault();
          }}
        />
        {q && (
          <button className="clear" aria-label="Clear search" onMouseDown={(e) => e.preventDefault()} onClick={() => setQ("")}>
            <Icon name="x" size={14} />
          </button>
        )}
      </div>
      {showList && (
        <ul className="results" id="search-results" role="listbox">
          {!rows && <li className="empty">Loading addresses…</li>}
          {rows && results.length === 0 && <li className="empty">No licensed shopfront matches “{q.trim()}”.</li>}
          {results.map((r, i) => (
            <li key={r[0]}>
              <button role="option" aria-selected={i === active} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(r)}>
                <PinMark n={r[4]} size={20} />
                <span style={{ minWidth: 0 }}>
                  <div className="r-title">{shortAddress(r[1])}</div>
                  <div className="r-sub">{r[2] || r[3].split(" | ")[0]}</div>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** "G/F, 100 PORTLAND STREET, YAU MA TEI" -> "G/F, 100 Portland Street, Yau Ma Tei" */
export function titleCase(s: string) {
  return s
    .toLowerCase()
    .replace(/(^|[\s,(])([a-z])/g, (_, p, c) => p + c.toUpperCase())
    .replace(/\b(G|Lg|Ug|M|B)\/f\b/gi, (m) => m.toUpperCase())
    .replace(/\bNo\.\s?/g, "No. ")
    .replace(/\b(\d+[a-z])\b/g, (m) => m.toUpperCase());
}

/** Address without the region: "G/F, 100 Portland Street, Yau Ma Tei" */
export function shortAddress(s: string) {
  return titleCase(s)
    .replace(/^ground floor\b/i, "G/F")
    .replace(/,\s*(kowloon|hong kong|new territories)\.?\s*$/i, "");
}
