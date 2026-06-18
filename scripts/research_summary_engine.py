import pandas as pd
from pathlib import Path

top_patterns_file = Path("data/top_patterns.csv")
signals_file = Path("data/all_stock_signals.csv")
output_file = Path("data/research_summary.txt")

summary_lines = []

# -----------------------------
# Top pattern summary
# -----------------------------
if top_patterns_file.exists():
    top_df = pd.read_csv(top_patterns_file)

    if not top_df.empty:
        print("Columns detected:", list(top_df.columns))

        required_cols = ["Signal", "Count", "WinRate5D", "AvgReturn5D"]
        missing = [c for c in required_cols if c not in top_df.columns]
        if missing:
            raise ValueError(f"Missing required columns in top_patterns.csv: {missing}")

        summary_lines.append("=== MARKET RESEARCH SUMMARY ===\n")

        for _, row in top_df.head(10).iterrows():
            line = (
                f"Signal: {row['Signal']} | "
                f"Trades: {int(row['Count'])} | "
                f"WinRate5D: {row['WinRate5D']:.3f} | "
                f"AvgReturn5D: {row['AvgReturn5D']:.5f}"
            )
            summary_lines.append(line)

        summary_lines.append("")

# -----------------------------
# Latest stock trend summary
# -----------------------------
if signals_file.exists():
    signals_df = pd.read_csv(signals_file)

    required_signal_cols = ["Date", "Ticker", "MarketRegime"]
    missing_signal_cols = [c for c in required_signal_cols if c not in signals_df.columns]
    if missing_signal_cols:
        raise ValueError(f"Missing required columns in all_stock_signals.csv: {missing_signal_cols}")

    signals_df["Date"] = pd.to_datetime(signals_df["Date"], errors="coerce")
    signals_df = signals_df.dropna(subset=["Date", "Ticker", "MarketRegime"]).copy()

    if not signals_df.empty:
        latest_date = signals_df["Date"].max()
        latest_df = signals_df[signals_df["Date"] == latest_date].copy()

        summary_lines.append(f"=== LATEST STOCK TREND SUMMARY ({latest_date.date()}) ===\n")

        for regime in ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "UNKNOWN"]:
            regime_stocks = latest_df[latest_df["MarketRegime"] == regime]["Ticker"].dropna().tolist()

            if regime_stocks:
                stock_text = ", ".join(regime_stocks[:15])
                if len(regime_stocks) > 15:
                    stock_text += ", ..."
                summary_lines.append(f"{regime}: {stock_text}")

        summary_lines.append("")

# -----------------------------
# Final output
# -----------------------------
summary_text = "\n".join(summary_lines)

print("\n" + summary_text)

with open(output_file, "w") as f:
    f.write(summary_text)

print(f"\nSaved summary to {output_file}")