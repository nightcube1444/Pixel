import { useState } from "react";
import { askMarketChat } from "./api";

function MarketChat() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setAnswer("");

    try {
      const result = await askMarketChat(question);
      setAnswer(result.answer || "No answer returned.");
    } catch (err) {
      setAnswer("Chat error. Check if Flask backend is running on port 5000.");
      console.error(err);
    }

    setLoading(false);
  };

  return (
    <div>
      <h2>Pixel AI Market Teacher</h2>

      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask: Why is JPM recommended? Explain PANIC|HIGH_VOLATILITY..."
        style={{
          width: "100%",
          minHeight: "80px",
          padding: "10px",
          background: "#050505",
          color: "white",
          border: "1px solid #333",
          borderRadius: "8px",
        }}
      />

      <button
        onClick={ask}
        disabled={loading}
        style={{
          marginTop: "10px",
          padding: "10px 14px",
          cursor: "pointer",
        }}
      >
        {loading ? "Thinking..." : "Ask Pixel"}
      </button>

      <div
        style={{
          marginTop: "16px",
          whiteSpace: "pre-wrap",
          lineHeight: "1.5",
          background: "#050505",
          border: "1px solid #222",
          borderRadius: "8px",
          padding: "12px",
        }}
      >
        {answer || "Ask a question to learn what the market data means."}
      </div>
    </div>
  );
}

export default MarketChat;