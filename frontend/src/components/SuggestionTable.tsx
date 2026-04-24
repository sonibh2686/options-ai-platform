import React, { useMemo, useState } from "react";

type Props = {
  items: any[];
  onSelect: (item: any) => void;
};

type SortKey =
  | "category"
  | "expiry"
  | "strike"
  | "option_type"
  | "mid_price"
  | "implied_volatility"
  | "delta"
  | "theta"
  | "pop"
  | "selected_strike_oi"
  | "oi_score"
  | "liquidity_score"
  | "greeks_score"
  | "total_score"
  | "recommendation";

function scoreClass(score: number) {
  if (score >= 78) return "score-strong";
  if (score >= 65) return "score-buy";
  if (score >= 50) return "score-neutral";
  return "score-avoid";
}

function compareValues(a: any, b: any, dir: "asc" | "desc") {
  const av = a ?? "";
  const bv = b ?? "";

  if (typeof av === "number" && typeof bv === "number") {
    return dir === "asc" ? av - bv : bv - av;
  }

  const as = String(av).toLowerCase();
  const bs = String(bv).toLowerCase();

  if (as < bs) return dir === "asc" ? -1 : 1;
  if (as > bs) return dir === "asc" ? 1 : -1;
  return 0;
}

export default function SuggestionTable({ items, onSelect }: Props) {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [recoFilter, setRecoFilter] = useState("ALL");
  const [expiryFilter, setExpiryFilter] = useState("ALL");
  const [minScore, setMinScore] = useState("");
  const [minOI, setMinOI] = useState("");
  const [minPOP, setMinPOP] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("total_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const categories = useMemo(
    () => Array.from(new Set(items.map((x) => x.category).filter(Boolean))),
    [items]
  );

  const expiries = useMemo(
    () => Array.from(new Set(items.map((x) => x.expiry).filter(Boolean))),
    [items]
  );

  const recommendations = useMemo(
    () => Array.from(new Set(items.map((x) => x.recommendation).filter(Boolean))),
    [items]
  );

  const filteredItems = useMemo(() => {
    const s = search.trim().toLowerCase();

    let data = items.filter((row) => {
      if (s) {
        const hay = [
          row.category,
          row.expiry,
          row.option_type,
          row.recommendation,
          row.ticker,
          row.strike,
        ]
          .join(" ")
          .toLowerCase();

        if (!hay.includes(s)) return false;
      }

      if (categoryFilter !== "ALL" && row.category !== categoryFilter) return false;
      if (typeFilter !== "ALL" && row.option_type !== typeFilter) return false;
      if (recoFilter !== "ALL" && row.recommendation !== recoFilter) return false;
      if (expiryFilter !== "ALL" && row.expiry !== expiryFilter) return false;
      if (minScore !== "" && Number(row.total_score) < Number(minScore)) return false;
      if (minOI !== "" && Number(row.selected_strike_oi) < Number(minOI)) return false;
      if (minPOP !== "" && Number(row.pop) * 100 < Number(minPOP)) return false;

      return true;
    });

    return [...data].sort((a, b) => compareValues(a[sortKey], b[sortKey], sortDir));
  }, [items, search, categoryFilter, typeFilter, recoFilter, expiryFilter, minScore, minOI, minPOP, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th style={{ cursor: "pointer" }} onClick={() => toggleSort(field)}>
      {label} {sortKey === field ? (sortDir === "asc" ? "▲" : "▼") : ""}
    </th>
  );

  return (
    <>
      <div className="panel" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Filters & Sorting</h3>

        <div className="filter-grid">
          <div>
            <label>Search</label>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="AAPL, call, weekly..." />
          </div>

          <div>
            <label>Category</label>
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="ALL">All</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div>
            <label>Type</label>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="ALL">All</option>
              <option value="call">Call</option>
              <option value="put">Put</option>
            </select>
          </div>

          <div>
            <label>Recommendation</label>
            <select value={recoFilter} onChange={(e) => setRecoFilter(e.target.value)}>
              <option value="ALL">All</option>
              {recommendations.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          <div>
            <label>Expiry</label>
            <select value={expiryFilter} onChange={(e) => setExpiryFilter(e.target.value)}>
              <option value="ALL">All</option>
              {expiries.map((e) => <option key={e} value={e}>{e}</option>)}
            </select>
          </div>

          <div>
            <label>Min Score</label>
            <input type="number" value={minScore} onChange={(e) => setMinScore(e.target.value)} />
          </div>

          <div>
            <label>Min OI</label>
            <input type="number" value={minOI} onChange={(e) => setMinOI(e.target.value)} />
          </div>

          <div>
            <label>Min POP %</label>
            <input type="number" value={minPOP} onChange={(e) => setMinPOP(e.target.value)} />
          </div>

          <div>
            <label>Sort By</label>
            <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
              <option value="total_score">Total Score</option>
              <option value="selected_strike_oi">OI</option>
              <option value="oi_score">OI Score</option>
              <option value="liquidity_score">Liquidity</option>
              <option value="greeks_score">Greeks</option>
              <option value="pop">POP</option>
              <option value="delta">Delta</option>
              <option value="theta">Theta</option>
              <option value="mid_price">Mid Price</option>
              <option value="strike">Strike</option>
              <option value="expiry">Expiry</option>
            </select>
          </div>

          <div>
            <label>Direction</label>
            <select value={sortDir} onChange={(e) => setSortDir(e.target.value as "asc" | "desc")}>
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
        </div>

        <div style={{ marginTop: 12, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            className="btn ghost"
            onClick={() => {
              setSearch("");
              setCategoryFilter("ALL");
              setTypeFilter("ALL");
              setRecoFilter("ALL");
              setExpiryFilter("ALL");
              setMinScore("");
              setMinOI("");
              setMinPOP("");
              setSortKey("total_score");
              setSortDir("desc");
            }}
          >
            Reset Filters
          </button>

          <div style={{ paddingTop: 10 }}>
            Showing <b>{filteredItems.length}</b> of <b>{items.length}</b> rows
          </div>
        </div>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <SortHeader label="Category" field="category" />
              <SortHeader label="Expiry" field="expiry" />
              <SortHeader label="Strike" field="strike" />
              <SortHeader label="Type" field="option_type" />
              <SortHeader label="Mid" field="mid_price" />
              <SortHeader label="IV" field="implied_volatility" />
              <SortHeader label="Δ" field="delta" />
              <SortHeader label="Θ" field="theta" />
              <SortHeader label="POP" field="pop" />
              <SortHeader label="OI" field="selected_strike_oi" />
              <SortHeader label="OI Score" field="oi_score" />
              <SortHeader label="Liquidity" field="liquidity_score" />
              <SortHeader label="Greeks" field="greeks_score" />
              <SortHeader label="Score" field="total_score" />
              <SortHeader label="Reco" field="recommendation" />
              <th>View</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((row, idx) => (
              <tr key={`${row.category}-${row.expiry}-${row.strike}-${idx}`}>
                <td>{row.category}</td>
                <td>{row.expiry}</td>
                <td>{row.strike}</td>
                <td>{row.option_type.toUpperCase()}</td>
                <td>{row.mid_price}</td>
                <td>{(row.implied_volatility * 100).toFixed(2)}%</td>
                <td>{row.delta}</td>
                <td>{row.theta}</td>
                <td>{(row.pop * 100).toFixed(1)}%</td>
                <td>{row.selected_strike_oi}</td>
                <td>{row.oi_score}</td>
                <td>{row.liquidity_score}</td>
                <td>{row.greeks_score}</td>
                <td className={scoreClass(row.total_score)}>{row.total_score}</td>
                <td>{row.recommendation}</td>
                <td><button className="btn small" onClick={() => onSelect(row)}>View</button></td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td colSpan={16} style={{ textAlign: "center", padding: 20 }}>
                  No rows match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}