import { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";
import {
  getWatchlist,
  getCandles,
  getLiveTicker,
  getSystemStatus,
  getFileStatus,
  getSystemHealth,
  getLivePatterns,
} from "./api";
import MarketDashboard from "./MarketDashboard";
import "./App.css";
 

function App() {
  const chartContainerRef = useRef(null);
  const [fileStatus, setFileStatus] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [livePatterns, setLivePatterns] = useState([]);
  const [view, setView] = useState("terminal");
  const [watchlist, setWatchlist] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState("");
  const [candles, setCandles] = useState([]);
  const [liveTicker, setLiveTicker] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [lastUpdated, setLastUpdated] = useState("");

  useEffect(() => {
    loadWatchlist();
    loadSystemStatus();
    loadFileStatus();
  }, []);

  useEffect(() => {
    if (selectedTicker) {
      loadCandles(selectedTicker);
      loadLiveTicker(selectedTicker);
      loadSystemStatus();
    }
  }, [selectedTicker]);

  useEffect(() => {
    if (!selectedTicker || view !== "terminal") return;

    const interval = setInterval(() => {
      loadWatchlist(false);
      loadCandles(selectedTicker);
      loadLiveTicker(selectedTicker);
      loadSystemStatus();
      loadFileStatus();
      loadSystemHealth();
      loadLivePatterns();
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedTicker, view]);

  useEffect(() => {
    if (view !== "terminal") return;
    if (!chartContainerRef.current || candles.length === 0) return;

    chartContainerRef.current.innerHTML = "";

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 420,
      layout: {
        background: { color: "#374151" },
        textColor: "#ffffff",
      },
      grid: {
        vertLines: { color: "#4b5563" },
        horzLines: { color: "#4b5563" },
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries);
    candleSeries.setData(candles);
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [candles, view]);

  const loadWatchlist = async (setDefaultTicker = true) => {
    try {
      const data = await getWatchlist();
      setWatchlist(data);
      setLastUpdated(new Date().toLocaleTimeString());

      if (setDefaultTicker && data.length > 0 && !selectedTicker) {
        setSelectedTicker(data[0].Ticker);
      }
    } catch (err) {
      console.error("Failed to load watchlist:", err);
    }
  };

  const loadCandles = async (ticker) => {
    try {
      const data = await getCandles(ticker);
      setCandles(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to load candles:", err);
    }
  };

  const loadLiveTicker = async (ticker) => {
    try {
      const data = await getLiveTicker(ticker);
      setLiveTicker(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to load live ticker:", err);
    }
  };

  const loadSystemStatus = async () => {
    try {
      const data = await getSystemStatus();
      setSystemStatus(data);
    } catch (err) {
      console.error("Failed to load system status:", err);
    }
  };
  const loadFileStatus = async () => {
    try {
      const data = await getFileStatus();
      setFileStatus(data);
    } catch (err) {
      console.error(err);
    }
  };
  const loadSystemHealth = async () => {
    try {
      const data = await getSystemHealth();
      setSystemHealth(data);
    } catch (err) {
      console.error("Failed to load system health:", err);
    }
  };
  const loadLivePatterns = async () => {
    try {
      const data = await getLivePatterns();
      setLivePatterns(data);
    } catch (err) {
      console.error("Failed to load live patterns:", err);
    }
  };

  const selectedStock = watchlist.find((x) => x.Ticker === selectedTicker);
  const pattern = liveTicker?.pattern || selectedStock?.Pattern || "";

  return (
    <div>
      <div
        style={{
          background: "#050505",
          padding: "12px",
          borderBottom: "1px solid #222",
        }}
      >
        <button onClick={() => setView("terminal")}>Terminal</button>

        <button
          onClick={() => setView("dashboard")}
          style={{ marginLeft: "10px" }}
        >
          Intelligence Dashboard
        </button>

        <span style={{ marginLeft: "16px", color: "#9ca3af" }}>
          Last updated: {lastUpdated || "Not yet"}
        </span>

        <span style={{ marginLeft: "20px", color: "#22c55e" }}>
          API Time: {systemStatus?.backend_time || "Waiting..."}
        </span>
      </div>

      {view === "dashboard" && <MarketDashboard />}

      {view === "terminal" && (
        <div className="dashboard">
          <div className="sidebar">
            <h2>PIXEL</h2>
            {systemHealth && (
              <div

                style={{
                  background: "#052e16",

                  padding: "12px",

                  borderRadius: "10px",

                  marginBottom: "15px",

                  textAlign: "left",

                }}
              >
                <h3>System Health</h3>

                <div>🟢 API: {systemHealth.api_status}</div>

                <div>🟢 Pipeline: {systemHealth.pipeline_status}</div>

                <div>Watchlist: {systemHealth.watchlist_count}</div>

                <div>Pattern Matches: {systemHealth.pattern_matches}</div>

                <div>Trade Signals: {systemHealth.trade_signals}</div>

                <div>
                Files Healthy: {systemHealth.healthy_files}/{systemHealth.total_files}
                 </div>
                 <div>Market State: {systemHealth.market_state}</div>

                 <div>SPY: {systemHealth.spy_regime}</div>

                <div>VIX: {systemHealth.vix_state}</div>

              </div>

            )}
            <div
              style={{
                background: "#111827",
                padding: "12px",
                borderRadius: "10px",
                marginBottom: "15px",
                textAlign: "left",
              }}
            >
              <h3>Pipeline Status</h3>
              {fileStatus.map((file, index) => (
                <div key={index}>
                  {file.exists ? "🟢" : "🔴"} {file.file}
                </div>
              ))}
            </div>
              
            <div className="panel">
            
            <div

              style={{

              background: "#111827",

              padding: "12px",

              borderRadius: "10px",

              marginBottom: "15px",

              textAlign: "left",

            }}
          >
             <h3>Top Live Pattern Matches</h3>
             {livePatterns.slice(0, 8).map((row, index) => (
              <div
                key={index}

                style={{
                  padding: "8px 0",

                    borderBottom: "1px solid #1f2937",

                  }}  
                >
                  <strong>{row.Ticker}</strong>

                  <div style={{ fontSize: "13px" }}>{row.Pattern}</div>

                  <div style={{ color: "#9ca3af", fontSize: "13px" }}>
                    Trust: {row.TrustLevel} | Alpha: {row.AlphaScore} | Win Rate:{" "}

                    {row.WinRate}%

                  </div>

                </div>

              ))}

            </div>
            
              <h3>Speculative Watchlist</h3>

              {watchlist.map((stock, i) => (
                <button
                  key={i}
                  className={
                    selectedTicker === stock.Ticker ? "ticker active" : "ticker"
                  }
                  onClick={() => setSelectedTicker(stock.Ticker)}
                >
                  {stock.Ticker}
                </button>
              ))}
            </div>
          </div>
          
          <div className="main">
            <div className="chart-panel">
              <h2>{selectedTicker} Candlestick Chart</h2>

              <p style={{ color: "#9ca3af" }}>
                Auto-refreshing candles and signals every 30 seconds
              </p>

              <div ref={chartContainerRef} className="chart-box"></div>
            </div>

            {selectedStock && (
              <div className="signals-panel">
                <h2>Live Research Signal</h2>

                <div className="signal">
                  Signal: {selectedStock.PrimarySignal}
                </div>
                <div className="signal">Score: {selectedStock.FinalScore}</div>
                <div className="signal">Action: {selectedStock.Action}</div>
                <div className="signal">Win Rate: {selectedStock.WinRate}</div>
                <div className="signal">Risk: {selectedStock.RiskLevel}</div>
                <div className="signal">
                  Pattern: {pattern || "No strong pattern"}
                </div>
              </div>
            )}
          </div>

          <div className="chat-panel">
            <h2>Live Pattern Detector</h2>

            {selectedStock && (
              <div className="explain-card">
                <h3>{selectedStock.Ticker}</h3>

                <p>
                  <strong>Current Pattern:</strong>
                </p>
                <p className="pattern-text">{pattern || "No strong pattern"}</p>

                <p>
                  <strong>Decision:</strong> {selectedStock.Action}
                </p>
                <p>
                  <strong>Signal:</strong> {selectedStock.PrimarySignal}
                </p>
                <p>
                  <strong>Score:</strong> {selectedStock.FinalScore}
                </p>
                <p>
                  <strong>Win Rate:</strong> {selectedStock.WinRate}%
                </p>
                <p>
                  <strong>Trades:</strong> {selectedStock.Trades}
                </p>

                <p>
                  <strong>Pattern Breakdown:</strong>
                </p>

                {liveTicker?.explanation?.length > 0 ? (
                  liveTicker.explanation.map((item, index) => (
                    <p key={index}>
                      <strong>{item.component}:</strong> {item.meaning}
                    </p>
                  ))
                ) : (
                  <p>No pattern explanation available yet.</p>
                )}

                <p>
                  <strong>Pixel Note:</strong>
                </p>
                <p>
                  {selectedStock.Action === "WATCH"
                    ? "Pixel is watching this setup. Research/paper-trade only."
                    : "Pixel does not see a clean trade setup right now."}
                </p>
              </div>
            )}

            {!selectedStock && (
              <p style={{ color: "#9ca3af" }}>
                Select a ticker to see live pattern explanation.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;