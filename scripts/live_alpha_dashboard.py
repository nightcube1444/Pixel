from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

signals_file = BASE_DIR / "data/latest_stock_signals.csv"
alpha_file = BASE_DIR / "data/alpha_ranking_results.csv"
market_file = BASE_DIR / "data/market_state.csv"

signals = pd.read_csv(signals_file)
alpha = pd.read_csv(alpha_file)
market = pd.read_csv(market_file)

print("\n================================")
print(" MINI CUBE ALPHA DASHBOARD")
print("================================\n")

# ------------------------
# Market State
# ------------------------

if not market.empty:

    latest_market = market.iloc[-1]

    print("MARKET STATE")
    print("------------------------")
    print("State:", latest_market["MarketState"])
    print("SPY Regime:", latest_market["SPY_Regime"])
    print("VIX State:", latest_market["VIX_State"])
    print()

# ------------------------
# Top Live Signals
# ------------------------

print("TOP LIVE SIGNALS")
print("------------------------")

top_signals = signals.sort_values(
    "FinalScore",
    ascending=False
).head(10)

print(
    top_signals[
        [
            "Ticker",
            "PrimarySignal",
            "MarketRegime",
            "FinalScore"
        ]
    ]
)

print()

# ------------------------
# Top Alpha Patterns
# ------------------------

print("TOP HISTORICAL PATTERNS")
print("------------------------")

print(
    alpha[
        [
            "AlphaRank",
            "Pattern",
            "Trades",
            "WinRate",
            "AlphaScore"
        ]
    ].head(10)
)

print()

# ------------------------
# Strongest Live Opportunity
# ------------------------

best_signal = top_signals.iloc[0]

print("BEST LIVE OPPORTUNITY")
print("------------------------")
print("Ticker:", best_signal["Ticker"])
print("Signal:", best_signal["PrimarySignal"])
print("Regime:", best_signal["MarketRegime"])
print("Score:", best_signal["FinalScore"])

print("\n================================")