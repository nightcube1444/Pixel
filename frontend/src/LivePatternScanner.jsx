import { useEffect, useState } from "react";
import { getLivePatterns } from "./api";

function LivePatternScanner() {
  const [patterns, setPatterns] = useState([]);

  useEffect(() => {
    loadPatterns();

    const interval = setInterval(() => {
      loadPatterns();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const loadPatterns = async () => {
    try {
      const data = await getLivePatterns();
      setPatterns(data);
    } catch (err) {
      console.error("Failed to load live patterns:", err);
    }
  };

  return (
    <div>
      <h2>Live Pattern Scanner</h2>

      {patterns.slice(0, 15).map((row, index) => (
        <div
          key={index}
          style={{
            border: "1px solid #222",
            padding: "10px",
            marginBottom: "8px",
            borderRadius: "8px",
            background: "#050505",
          }}
        >
          <strong>{row.Ticker}</strong>
          <div>{row.Pattern}</div>
          <div>
            Trust: {row.TrustLevel} | Alpha: {row.AlphaScore} | Win Rate:{" "}
            {row.WinRate}
          </div>
        </div>
      ))}
    </div>
  );
}

export default LivePatternScanner;