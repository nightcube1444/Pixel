from pathlib import Path
from datetime import datetime
import pandas as pd

REPORT_PATH = Path("data/daily_report.txt")

MARKET_STATE_PATH = Path("data/market_state.csv")
SIGNALS_PATH = Path("data/latest_stock_signals.csv")
PATTERNS_PATH = Path("data/live_pattern_matches.csv")
RECOMMENDATIONS_PATH = Path("data/context_aware_recommendations.csv")
PORTFOLIO_PATH = Path("data/model_portfolio.csv")
OPEN_TRADES_PATH = Path("data/open_paper_positions.csv")
TRADE_LOG_PATH = Path("data/paper_trade_log.csv")


def safe_read(path):
    if not path.exists():
        return None

    try:
        df = pd.read_csv(path)

        if df.empty:
            return None

        return df

    except Exception:
        return None


report = []

report.append("=" * 50)
report.append("MINI CUBE DAILY REPORT")
report.append("=" * 50)
report.append("")
report.append(
    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
report.append("")

# ===================================
# MARKET STATE
# ===================================

market_df = safe_read(MARKET_STATE_PATH)

report.append("MARKET STATE")
report.append("-" * 30)

if market_df is not None:

    latest = market_df.iloc[-1]

    report.append(
        f"Market State: {latest['MarketState']}"
    )

    report.append(
        f"SPY Regime: {latest['SPY_Regime']}"
    )

    report.append(
        f"VIX State: {latest['VIX_State']}"
    )

else:
    report.append("No market state available.")

report.append("")

# ===================================
# TOP SIGNALS
# ===================================

signals_df = safe_read(SIGNALS_PATH)

report.append("TOP SIGNALS")
report.append("-" * 30)

if signals_df is not None:

    top_signals = signals_df.sort_values(
        "FinalScore",
        ascending=False
    ).head(10)

    for _, row in top_signals.iterrows():

        report.append(
            f"{row['Ticker']} | "
            f"{row['PrimarySignal']} | "
            f"{row['MarketRegime']} | "
            f"Score={row['FinalScore']}"
        )

else:
    report.append("No signals available.")

report.append("")

# ===================================
# PATTERN MATCHES
# ===================================

pattern_df = safe_read(PATTERNS_PATH)

report.append("LIVE PATTERN MATCHES")
report.append("-" * 30)

if pattern_df is not None:

    for _, row in pattern_df.head(10).iterrows():

        report.append(
            f"{row['Ticker']} | "
            f"Alpha={round(row['AlphaScore'],2)} | "
            f"WinRate={round(row['WinRate'],2)}%"
        )

else:
    report.append("No pattern matches.")

report.append("")

# ===================================
# RECOMMENDATIONS
# ===================================

rec_df = safe_read(RECOMMENDATIONS_PATH)

report.append("RECOMMENDATIONS")
report.append("-" * 30)

if rec_df is not None:

    for _, row in rec_df.iterrows():

        report.append(
            f"{row['Ticker']} | "
            f"{row['Recommendation']} | "
            f"Score={round(row['AdjustedAlphaScore'],2)}"
        )

else:
    report.append("No recommendations.")

report.append("")

# ===================================
# MODEL PORTFOLIO
# ===================================

portfolio_df = safe_read(PORTFOLIO_PATH)

report.append("MODEL PORTFOLIO")
report.append("-" * 30)

if portfolio_df is not None:

    for _, row in portfolio_df.iterrows():

        report.append(
            f"{row['Ticker']} | "
            f"{round(row['WeightPct'],2)}%"
        )

else:
    report.append("No portfolio.")

report.append("")

# ===================================
# OPEN TRADES
# ===================================

open_df = safe_read(OPEN_TRADES_PATH)

report.append("OPEN PAPER TRADES")
report.append("-" * 30)

if open_df is not None:

    for _, row in open_df.iterrows():

        report.append(
            f"{row['Ticker']} | "
            f"{row['PrimarySignal']} | "
            f"Entry={round(row['EntryPrice'],2)}"
        )

else:
    report.append("No open trades.")

report.append("")

# ===================================
# CLOSED TRADES
# ===================================

trade_df = safe_read(TRADE_LOG_PATH)

report.append("CLOSED TRADES")
report.append("-" * 30)

if trade_df is not None:

    recent = trade_df.tail(10)

    for _, row in recent.iterrows():

        report.append(
            f"{row['Ticker']} | "
            f"{row['ReturnPct']}% | "
            f"{row['ExitReason']}"
        )

else:
    report.append("No completed trades.")

report.append("")
report.append("=" * 50)

REPORT_PATH.write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n".join(report))
print(f"\nSaved to {REPORT_PATH}")