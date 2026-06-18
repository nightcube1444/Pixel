import pandas as pd
from pathlib import Path

benchmark_path = Path("data/benchmark_context.csv")
news_path = Path("data/news_signals.csv")
output_path = Path("data/market_state.csv")

if not benchmark_path.exists():
    raise FileNotFoundError(f"Missing file: {benchmark_path}")

bench = pd.read_csv(benchmark_path)

required_bench_cols = ["Date", "SPY_Regime", "VIX_State"]
missing_bench = [c for c in required_bench_cols if c not in bench.columns]
if missing_bench:
    raise ValueError(f"Missing benchmark columns: {missing_bench}")

bench["Date"] = pd.to_datetime(bench["Date"], errors="coerce")
bench = bench.dropna(subset=["Date"]).copy()

if news_path.exists():
    news = pd.read_csv(news_path)

    required_news_cols = ["Date", "FearScore"]
    missing_news = [c for c in required_news_cols if c not in news.columns]
    if missing_news:
        raise ValueError(f"Missing news columns: {missing_news}")

    news["Date"] = pd.to_datetime(news["Date"], errors="coerce")
    news = news.dropna(subset=["Date"]).copy()

    df = pd.merge(
        bench,
        news[["Date", "FearScore", "PositiveScore", "HeadlineCount"]],
        on="Date",
        how="left"
    )
else:
    df = bench.copy()
    df["FearScore"] = 0
    df["PositiveScore"] = 0
    df["HeadlineCount"] = 0

df["FearScore"] = df["FearScore"].fillna(0)
df["PositiveScore"] = df["PositiveScore"].fillna(0)
df["HeadlineCount"] = df["HeadlineCount"].fillna(0)

df["SPY_Regime"] = df["SPY_Regime"].ffill()

df["VIX_State"] = df["VIX_State"].ffill()

def classify_market_state(row):
    spy_regime = str(row["SPY_Regime"]).upper()
    vix_state = str(row["VIX_State"]).upper()
    fear_score = row["FearScore"]
    positive_score = row["PositiveScore"]

    if spy_regime == "BULL" and vix_state == "VIX_LOW" and fear_score <= 3:
        return "RISK_ON"

    if spy_regime in ["BEAR", "SIDEWAYS"] and vix_state in ["VIX_HIGH", "VIX_EXTREME"] and fear_score >= 5:
        return "RISK_OFF"

    if spy_regime == "BULL" and vix_state == "VIX_ELEVATED":
        return "TENSE_BULL"

    if spy_regime == "BULL" and vix_state == "VIX_HIGH":
        return "RISK_OFF_WARNING"

    if spy_regime == "SIDEWAYS" and vix_state == "VIX_LOW":
        return "CALM_SIDEWAYS"

    if positive_score > fear_score and spy_regime == "BULL":
        return "POSITIVE_BIAS"

    return "TRANSITION"

df = df.sort_values("Date").reset_index(drop=True)
df["MarketState"] = df.apply(classify_market_state, axis=1)

df["PrevMarketState"] = df["MarketState"].shift(1)
df["RegimeShiftFlag"] = df["MarketState"] != df["PrevMarketState"]
df.loc[df.index == 0, "RegimeShiftFlag"] = False

df.to_csv(output_path, index=False)

print(f"Saved to {output_path}")
print(df.tail(20))