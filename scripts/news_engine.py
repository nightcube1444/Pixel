from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/news_data.csv")
OUTPUT_PATH = Path("data/news_signals.csv")

if not INPUT_PATH.exists():
    raise FileNotFoundError(f"Missing file: {INPUT_PATH}")

news_df = pd.read_csv(INPUT_PATH)

if news_df.empty:
    raise ValueError("news_data.csv is empty.")

required_cols = ["Date", "Headline"]
missing_cols = [c for c in required_cols if c not in news_df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

news_df["Date"] = pd.to_datetime(news_df["Date"], errors="coerce")
news_df = news_df.dropna(subset=["Date", "Headline"]).copy()
news_df["Headline"] = news_df["Headline"].astype(str).str.lower().str.strip()

fear_keywords = [
    "crash", "panic", "fear", "war", "selloff", "drop", "downgrade",
    "recession", "inflation", "layoffs", "bankruptcy", "loss", "fall",
    "collapse", "bear market", "sanction", "outage"
]

positive_keywords = [
    "surge", "growth", "beats", "upgrade", "rally", "profit", "strong",
    "record", "bull market", "recovery", "expands", "gain", "rise",
    "improves", "partnership", "demand"
]

def keyword_score(text: str, keywords: list[str]) -> int:
    score = 0
    for word in keywords:
        if word in text:
            score += 1
    return score

news_df["FearScore"] = news_df["Headline"].apply(lambda x: keyword_score(x, fear_keywords))
news_df["PositiveScore"] = news_df["Headline"].apply(lambda x: keyword_score(x, positive_keywords))

daily = news_df.groupby("Date").agg(
    FearScore=("FearScore", "sum"),
    PositiveScore=("PositiveScore", "sum"),
    HeadlineCount=("Headline", "count")
).reset_index()

daily["Date"] = daily["Date"].dt.date

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
daily.to_csv(OUTPUT_PATH, index=False)

print(f"Saved {len(daily)} rows to {OUTPUT_PATH}")
print(daily.head(20))