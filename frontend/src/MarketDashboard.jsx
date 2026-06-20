import { useEffect, useState } from "react";
import { getMarketDashboard } from "./api";
import MarketChat from "./MarketChat";
import LivePatternScanner from "./LivePatternScanner";

function Card({ children }) {
  return (
    <div
      style={{
        border: "1px solid #222",
        background: "#0b0b0b",
        padding: "14px",
        borderRadius: "10px",
        marginBottom: "12px",
      }}
    >
      {children}
    </div>
  );
}

function MarketDashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getMarketDashboard()
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) {
    return <div style={{ color: "white", padding: 20 }}>Loading dashboard...</div>;
  }

  return (
    <div style={{ color: "white" }}>
      <h1>PIXEL MARKET INTELLIGENCE</h1>

      <Card>
        <h2>Market State</h2>
        <p>Market State: {data.market_state?.MarketState || "N/A"}</p>
        <p>SPY Regime: {data.market_state?.SPY_Regime || "N/A"}</p>
        <p>VIX State: {data.market_state?.VIX_State || "N/A"}</p>
      </Card>

      <Card>
        <h2>Top Recommendations</h2>
        {data.top_recommendations?.map((row, index) => (
          <div key={index} style={{ marginBottom: "10px" }}>
            <strong>
              {row.RecommendationRank}. {row.Ticker}
            </strong>
            <div>Sector: {row.Sector}</div>
            <div>Score: {row.OpportunityScore}</div>
            <div>
              Alpha: {row.AlphaScore} | Survival: {row.SurvivalScore}
            </div>
          </div>
        ))}
      </Card>

      <Card>
        <h2>Live Pattern Matches</h2>
        {data.live_patterns?.slice(0, 8).map((row, index) => (
          <div key={index} style={{ marginBottom: "10px" }}>
            <strong>{row.Ticker}</strong>
            <div>{row.Pattern}</div>
            <div>
              Trust: {row.TrustLevel} | Alpha: {row.AlphaScore}
            </div>
          </div>
        ))}
      </Card>

      <Card>
        <h2>Top Institutional Patterns</h2>
        {data.top_patterns?.slice(0, 8).map((row, index) => (
          <div key={index} style={{ marginBottom: "10px" }}>
            <strong>Rank {row.InstitutionalRank}</strong>
            <div>{row.Pattern}</div>
            <div>
              Appearances: {row.Appearances} | Avg 10D: {row.AvgReturn10D}
            </div>
            <div>Survival: {row.SurvivalScore}</div>
          </div>
        ))}
      </Card>

      <Card>
        <h2>Top Sectors</h2>
        {data.top_sectors?.map((row, index) => (
          <div key={index}>
            {row.SectorRank}. {row.Sector} — Score: {row.SectorAlphaScore}
          </div>
        ))}
      </Card>
      <Card>
        <MarketChat />
      </Card>
      <Card>
        <LivePatternScanner />
      </Card>
    </div>
  );
}

export default MarketDashboard;