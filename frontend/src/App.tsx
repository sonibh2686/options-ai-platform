import React, { useEffect, useState } from "react";
import { analyzeTrade, fetchExpiries, fetchHistory, scanGlobal, scanToday } from "./api";
import ScoreCard from "./components/ScoreCard";
import SuggestionTable from "./components/SuggestionTable";
import TradeDetail from "./components/TradeDetail";
import StrategyPanel from "./components/StrategyPanel";
import "./styles.css";

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState("");
  const [manualStrike, setManualStrike] = useState("200");
  const [manualType, setManualType] = useState("call");
  const [action, setAction] = useState("buy");
  const [strikeWindow, setStrikeWindow] = useState(10);

  const [scanResult, setScanResult] = useState<any>(null);
  const [todayScanResult, setTodayScanResult] = useState<any>(null);
  const [manualResult, setManualResult] = useState<any>(null);
  const [selectedTrade, setSelectedTrade] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  const [loadingExpiries, setLoadingExpiries] = useState(false);
  const [loadingScan, setLoadingScan] = useState(false);
  const [loadingToday, setLoadingToday] = useState(false);
  const [loadingManual, setLoadingManual] = useState(false);
  const [error, setError] = useState("");

  const loadExpiries = async (symbol: string) => {
    if (!symbol.trim()) return;

    setLoadingExpiries(true);
    setError("");

    try {
      const data = await fetchExpiries(symbol.toUpperCase());
      const expiryList = data.expiries || [];
      setExpiries(expiryList);
      setSelectedExpiry(expiryList[0] || "");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load expiries");
      setExpiries([]);
      setSelectedExpiry("");
    } finally {
      setLoadingExpiries(false);
    }
  };

  const loadHistory = async (symbol: string) => {
    if (!symbol.trim()) return;

    try {
      const data = await fetchHistory(symbol.toUpperCase());
      setHistory(data.items || []);
    } catch {
      setHistory([]);
    }
  };

  useEffect(() => {
    loadExpiries(ticker);
    loadHistory(ticker);
  }, []);

  const onTickerBlur = async () => {
    await loadExpiries(ticker.toUpperCase());
    await loadHistory(ticker.toUpperCase());
  };

  const runGlobalScan = async () => {
    if (!ticker.trim()) {
      setError("Ticker is required");
      return;
    }

    setLoadingScan(true);
    setError("");

    try {
      const data = await scanGlobal({
        ticker: ticker.toUpperCase(),
        strike_window: strikeWindow,
        min_open_interest: 50,
        min_volume: 1,
        include_calls: true,
        include_puts: true,
        action,
      });

      setScanResult(data);

      const first =
        data?.categories?.best_call_today ||
        data?.categories?.best_put_today ||
        data?.categories?.best_weekly ||
        data?.categories?.best_swing_option ||
        data?.ranked_list?.[0] ||
        null;

      setSelectedTrade(first);
      await loadHistory(ticker.toUpperCase());
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Global scan failed");
    } finally {
      setLoadingScan(false);
    }
  };

  const runTodayScan = async () => {
    if (!ticker.trim()) {
      setError("Ticker is required");
      return;
    }

    setLoadingToday(true);
    setError("");

    try {
      const data = await scanToday({
        ticker: ticker.toUpperCase(),
        strike_window: strikeWindow,
        min_open_interest: 50,
        min_volume: 1,
        action,
      });

      setTodayScanResult(data);

      setSelectedTrade(
        data?.best_call_today ||
          data?.best_put_today ||
          data?.ranked_today?.[0] ||
          null
      );
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Today scan failed");
    } finally {
      setLoadingToday(false);
    }
  };

  const runManualAnalysis = async () => {
    if (!ticker.trim()) {
      setError("Ticker is required");
      return;
    }

    if (!selectedExpiry) {
      setError("Please select an expiry");
      return;
    }

    if (!manualStrike || Number(manualStrike) <= 0) {
      setError("Strike must be greater than 0");
      return;
    }

    setLoadingManual(true);
    setError("");

    try {
      const data = await analyzeTrade({
        ticker: ticker.toUpperCase(),
        strike: Number(manualStrike),
        expiry: selectedExpiry,
        option_type: manualType,
        action,
      });

      setManualResult(data);
      setSelectedTrade(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Manual analysis failed");
    } finally {
      setLoadingManual(false);
    }
  };

  const globalCategories = scanResult?.categories || {};

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1>AI Options Trade Suggestion Engine</h1>
          <p>
            Validate a specific contract, scan best call/put today, or run a full
            global strategy scan with ranked opportunities.
          </p>
        </div>
      </div>

      <div className="panel">
        <div className="form-grid">
          <div>
            <label>Ticker</label>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              onBlur={onTickerBlur}
              placeholder="AAPL"
            />
          </div>

          <div>
            <label>Expiry</label>
            <select
              value={selectedExpiry}
              onChange={(e) => setSelectedExpiry(e.target.value)}
            >
              <option value="">Select expiry</option>
              {expiries.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label>Strike Window</label>
            <input
              type="number"
              value={strikeWindow}
              onChange={(e) => setStrikeWindow(Number(e.target.value))}
            />
          </div>

          <div>
            <label>Action</label>
            <select value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </div>

          <div>
            <label>Manual Strike</label>
            <input
              value={manualStrike}
              onChange={(e) => setManualStrike(e.target.value)}
              placeholder="200"
            />
          </div>

          <div>
            <label>Manual Type</label>
            <select
              value={manualType}
              onChange={(e) => setManualType(e.target.value)}
            >
              <option value="call">Call</option>
              <option value="put">Put</option>
            </select>
          </div>
        </div>

        <div className="button-row">
          <button className="btn" onClick={runTodayScan}>
            {loadingToday ? "Scanning Today..." : "Best Call/Put Today"}
          </button>

          <button className="btn" onClick={runGlobalScan}>
            {loadingScan ? "Scanning Global..." : "Run Global Scan"}
          </button>

          <button className="btn secondary" onClick={runManualAnalysis}>
            {loadingManual ? "Analyzing..." : "Validate My Input"}
          </button>

          <button
            className="btn ghost"
            onClick={() => loadExpiries(ticker.toUpperCase())}
          >
            {loadingExpiries ? "Refreshing..." : "Refresh Expiries"}
          </button>
        </div>

        {error ? <div className="error">{error}</div> : null}
      </div>

      {todayScanResult ? (
        <>
          <div className="grid-cards">
            <ScoreCard
              title="Best Call Today"
              value={
                todayScanResult.best_call_today
                  ? `${todayScanResult.best_call_today.strike}C`
                  : "N/A"
              }
              subtitle={
                todayScanResult.best_call_today
                  ? `${todayScanResult.best_call_today.expiry} | ${todayScanResult.best_call_today.total_score}`
                  : ""
              }
            />

            <ScoreCard
              title="Best Put Today"
              value={
                todayScanResult.best_put_today
                  ? `${todayScanResult.best_put_today.strike}P`
                  : "N/A"
              }
              subtitle={
                todayScanResult.best_put_today
                  ? `${todayScanResult.best_put_today.expiry} | ${todayScanResult.best_put_today.total_score}`
                  : ""
              }
            />

            <ScoreCard title="Today Expiry" value={todayScanResult.expiry || "N/A"} />
            <ScoreCard
              title="Underlying Price"
              value={todayScanResult.underlying_price ?? "N/A"}
            />
          </div>

          {todayScanResult?.strategy_recommendation ? (
            <StrategyPanel strategy={todayScanResult.strategy_recommendation} />
          ) : null}

          <div className="panel">
            <h2>Today Ranked List</h2>
            <SuggestionTable
              items={todayScanResult.ranked_today || []}
              onSelect={setSelectedTrade}
            />
          </div>
        </>
      ) : null}

      {scanResult ? (
        <>
          <div className="grid-cards">
            <ScoreCard title="Ticker" value={scanResult.ticker} />
            <ScoreCard
              title="Underlying Price"
              value={scanResult.underlying_price}
            />
            <ScoreCard
              title="Stock Strength"
              value={scanResult.stock_score}
              subtitle={scanResult.stock_bias}
            />
            <ScoreCard title="News Score" value={scanResult.news_score} />
          </div>

          {scanResult?.strategy_recommendation ? (
            <StrategyPanel strategy={scanResult.strategy_recommendation} />
          ) : null}

          <div className="grid-cards">
            <ScoreCard
              title="Best Call Today"
              value={
                globalCategories.best_call_today
                  ? `${globalCategories.best_call_today.strike}C`
                  : "N/A"
              }
              subtitle={
                globalCategories.best_call_today
                  ? `${globalCategories.best_call_today.expiry} | ${globalCategories.best_call_today.total_score}`
                  : ""
              }
            />

            <ScoreCard
              title="Best Put Today"
              value={
                globalCategories.best_put_today
                  ? `${globalCategories.best_put_today.strike}P`
                  : "N/A"
              }
              subtitle={
                globalCategories.best_put_today
                  ? `${globalCategories.best_put_today.expiry} | ${globalCategories.best_put_today.total_score}`
                  : ""
              }
            />

            <ScoreCard
              title="Best Weekly"
              value={
                globalCategories.best_weekly
                  ? `${globalCategories.best_weekly.strike} ${globalCategories.best_weekly.option_type.toUpperCase()}`
                  : "N/A"
              }
              subtitle={
                globalCategories.best_weekly
                  ? `${globalCategories.best_weekly.expiry} | ${globalCategories.best_weekly.total_score}`
                  : ""
              }
            />

            <ScoreCard
              title="Best Swing Option"
              value={
                globalCategories.best_swing_option
                  ? `${globalCategories.best_swing_option.strike} ${globalCategories.best_swing_option.option_type.toUpperCase()}`
                  : "N/A"
              }
              subtitle={
                globalCategories.best_swing_option
                  ? `${globalCategories.best_swing_option.expiry} | ${globalCategories.best_swing_option.total_score}`
                  : ""
              }
            />
          </div>

          <div className="panel">
            <h2>Global Ranked List</h2>
            <SuggestionTable
              items={scanResult.ranked_list || []}
              onSelect={setSelectedTrade}
            />
          </div>
        </>
      ) : null}

      {manualResult ? (
        <div className="panel">
          <h2>Manual Validation Result</h2>
          <div className="manual-row">
            <div>
              <b>Strike:</b> {manualResult.strike}
            </div>
            <div>
              <b>Type:</b> {manualResult.option_type}
            </div>
            <div>
              <b>Expiry:</b> {manualResult.expiry}
            </div>
            <div>
              <b>Recommendation:</b> {manualResult.recommendation}
            </div>
            <div>
              <b>Score:</b> {manualResult.total_score}
            </div>
          </div>
        </div>
      ) : null}

      <TradeDetail trade={selectedTrade} />

      <div className="two-col">
        <div className="panel">
          <h2>Recent News Headlines</h2>
          <ul>
            {(scanResult?.headlines ||
              todayScanResult?.headlines ||
              []
            ).map((h: string, i: number) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h2>Scan History</h2>
          <div className="history-list">
            {history.map((item, i) => (
              <div className="history-item" key={i}>
                <div>
                  <b>{item.mode}</b>
                </div>
                <div>
                  {item.option_type?.toUpperCase()} | {item.expiry}
                </div>
                <div>Score: {item.score}</div>
                <div>{item.recommendation}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}