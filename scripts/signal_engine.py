import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MARKET_DATA_PATH = BASE_DIR / "data/market_data.csv"
ALL_SIGNALS_PATH = BASE_DIR / "data/all_stock_signals.csv"
LATEST_SIGNALS_PATH = BASE_DIR / "data/latest_stock_signals.csv"
LEARNING_SCORES_PATH = BASE_DIR / "data/pattern_learning_scores.csv"


def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(series, short_period=12, long_period=26, signal_period=9):
    ema_short = series.ewm(span=short_period, adjust=False).mean()
    ema_long = series.ewm(span=long_period, adjust=False).mean()

    macd = ema_short - ema_long
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    hist = macd - signal

    return macd, signal, hist

def classify_market_regime(row):
    close_price = row["Close"]
    ma50 = row["MA50"]
    ma200 = row["MA200"]
    vol20 = row["RollingVol20"]

    if pd.isna(close_price):
        return "UNKNOWN"

    # Not enough history for indicators
    if pd.isna(ma50) or pd.isna(ma200) or pd.isna(vol20):
        return "INSUFFICIENT_HISTORY"

    if vol20 >= 0.03:
        return "HIGH_VOLATILITY"

    if close_price > ma50 and ma50 > ma200:
        return "BULL"

    if close_price < ma50 and ma50 < ma200:
        return "BEAR"

    return "SIDEWAYS"

def get_primary_signal(row):
    if row["Panic"] == "PANIC":
        return "PANIC"
    if row["Momentum"] == "MOMENTUM":
        return "MOMENTUM"
    if row["Volatility"] == "VOLATILE":
        return "VOLATILE"
    if row["RSI_Oversold"] == "OVERSOLD":
        return "OVERSOLD"
    if row["RSI_Overbought"] == "OVERBOUGHT":
        return "OVERBOUGHT"
    return "NONE"


def build_pattern_base(row):
    primary_signal = row["PrimarySignal"]
    regime = row["MarketRegime"]
    volatility = row["Volatility"]

    if pd.isna(primary_signal):
        primary_signal = "NONE"
    if pd.isna(regime):
        regime = "UNKNOWN"
    if pd.isna(volatility) or str(volatility).strip() == "":
        volatility = "NORMAL"

    return f"{primary_signal}|{regime}|{volatility}"


def load_learning_scores() -> pd.DataFrame:
    if not LEARNING_SCORES_PATH.exists():
        return pd.DataFrame(columns=["PatternKey", "ScoreAdjustment"])

    try:
        df = pd.read_csv(LEARNING_SCORES_PATH)
    except Exception as e:
        print(f"Failed to read learning scores: {e}")
        return pd.DataFrame(columns=["PatternKey", "ScoreAdjustment"])

    if df.empty:
        return pd.DataFrame(columns=["PatternKey", "ScoreAdjustment"])

    if "PatternKey" not in df.columns:
        return pd.DataFrame(columns=["PatternKey", "ScoreAdjustment"])

    if "ScoreAdjustment" not in df.columns:
        df["ScoreAdjustment"] = 0

    df["PatternKey"] = df["PatternKey"].astype(str).str.strip()
    df["ScoreAdjustment"] = pd.to_numeric(df["ScoreAdjustment"], errors="coerce").fillna(0)

    return df[["PatternKey", "ScoreAdjustment"]].copy()


def main():
    if not MARKET_DATA_PATH.exists():
        print(f"Missing file: {MARKET_DATA_PATH}")
        raise SystemExit(1)

    df = pd.read_csv(MARKET_DATA_PATH)

    required_cols = ["Date", "Ticker", "Close"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"market_data.csv is missing columns: {missing_cols}")
        raise SystemExit(1)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Ticker", "Close"]).copy()
    df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

    tickers = df["Ticker"].dropna().unique().tolist()
    all_signals = []

    for ticker in tickers:
        ticker_df = df[df["Ticker"] == ticker].copy()

        if ticker_df.empty:
            continue

        ticker_df = ticker_df.sort_values("Date").reset_index(drop=True)
        close_prices = pd.to_numeric(ticker_df["Close"], errors="coerce")

        signals = pd.DataFrame()
        signals["Date"] = ticker_df["Date"]
        signals["Ticker"] = ticker
        signals["Close"] = close_prices.values
        signals["Daily Return"] = close_prices.pct_change().values
        signals["RSI"] = calculate_rsi(close_prices).values

        signals["MA50"] = close_prices.rolling(50).mean().values
        signals["MA200"] = close_prices.rolling(200).mean().values
        signals["RollingVol20"] = close_prices.pct_change().rolling(20).std().values

        macd, macd_signal, hist = calculate_macd(close_prices)
        signals["MACD"] = macd.values
        signals["MACD_Signal"] = macd_signal.values
        signals["MACD_Hist"] = hist.values

        signals["Panic"] = signals["Daily Return"].apply(
            lambda x: "PANIC" if pd.notna(x) and x <= -0.01 else ""
        )

        signals["Momentum"] = signals["Daily Return"].apply(
            lambda x: "MOMENTUM" if pd.notna(x) and x >= 0.01 else ""
        )

        signals["Volatility"] = signals["Daily Return"].apply(

        lambda x: (
            "VOLATILE"
            if pd.notna(x) and abs(x) >= 0.015
            else "NORMAL"
        )
    )
        signals["RSI_Overbought"] = signals["RSI"].apply(
            lambda x: "OVERBOUGHT" if pd.notna(x) and x >= 75 else ""
        )

        signals["RSI_Oversold"] = signals["RSI"].apply(
            lambda x: "OVERSOLD" if pd.notna(x) and x <= 25 else ""
        )

        signals["MarketRegime"] = signals.apply(classify_market_regime, axis=1)
        signals["PrimarySignal"] = signals.apply(get_primary_signal, axis=1)
        signals["PatternBase"] = signals.apply(build_pattern_base, axis=1)

        # Base score from current technical logic
        signals["BaseScore"] = 0

        signals.loc[signals["PrimarySignal"] == "PANIC", "BaseScore"] += 50
        signals.loc[signals["PrimarySignal"] == "MOMENTUM", "BaseScore"] += 40
        signals.loc[signals["PrimarySignal"] == "VOLATILE", "BaseScore"] += 30
        signals.loc[signals["PrimarySignal"] == "OVERSOLD", "BaseScore"] += 20
        signals.loc[signals["PrimarySignal"] == "OVERBOUGHT", "BaseScore"] += 10

        signals.loc[signals["MarketRegime"] == "HIGH_VOLATILITY", "BaseScore"] += 15
        signals.loc[signals["MarketRegime"] == "BEAR", "BaseScore"] += 10
        signals.loc[signals["MarketRegime"] == "BULL", "BaseScore"] += 8
        signals.loc[signals["MarketRegime"] == "SIDEWAYS", "BaseScore"] += 5

        all_signals.append(signals)

    if not all_signals:
        print("No signals generated.")
        raise SystemExit(1)

    final_signals = pd.concat(all_signals, ignore_index=True)
    final_signals = final_signals.sort_values(["Ticker", "Date"]).reset_index(drop=True)

    # Merge learned adjustments
    learning_scores = load_learning_scores()

    final_signals = final_signals.merge(
        learning_scores,
        how="left",
        left_on="PatternBase",
        right_on="PatternKey"
    )

    final_signals["ScoreAdjustment"] = pd.to_numeric(
        final_signals["ScoreAdjustment"], errors="coerce"
    ).fillna(0)

    final_signals["FinalScore"] = final_signals["BaseScore"] + final_signals["ScoreAdjustment"]

    # Latest row per stock
    latest_signals = (
        final_signals
        .sort_values("Date")
        .groupby("Ticker")
        .tail(1)
        .sort_values(["Date", "Ticker"])
        .reset_index(drop=True)
    )

    # Save both
    ALL_SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_signals.to_csv(ALL_SIGNALS_PATH, index=False)
    latest_signals.to_csv(LATEST_SIGNALS_PATH, index=False)

    # Debug category counts from latest rows only
    bull = latest_signals[latest_signals["MarketRegime"] == "BULL"]["Ticker"].tolist()
    bear = latest_signals[latest_signals["MarketRegime"] == "BEAR"]["Ticker"].tolist()
    sideways = latest_signals[latest_signals["MarketRegime"] == "SIDEWAYS"]["Ticker"].tolist()
    high_volatility = latest_signals[latest_signals["MarketRegime"] == "HIGH_VOLATILITY"]["Ticker"].tolist()

    panic = latest_signals[latest_signals["Panic"] == "PANIC"]["Ticker"].tolist()
    momentum = latest_signals[latest_signals["Momentum"] == "MOMENTUM"]["Ticker"].tolist()
    oversold = latest_signals[latest_signals["RSI_Oversold"] == "OVERSOLD"]["Ticker"].tolist()
    overbought = latest_signals[latest_signals["RSI_Overbought"] == "OVERBOUGHT"]["Ticker"].tolist()

    print("\nLATEST SIGNALS:")
    print(latest_signals[[
        "Date",
        "Ticker",
        "Close",
        "MarketRegime",
        "PrimarySignal",
        "PatternBase",
        "BaseScore",
        "ScoreAdjustment",
        "FinalScore"
    ]].head(20))

    print("\nDEBUG CATEGORY COUNTS:")
    print("Bull:", len(bull), bull[:10])
    print("Bear:", len(bear), bear[:10])
    print("Sideways:", len(sideways), sideways[:10])
    print("High Volatility:", len(high_volatility), high_volatility[:10])
    print("Panic:", len(panic), panic[:10])
    print("Momentum:", len(momentum), momentum[:10])
    print("Oversold:", len(oversold), oversold[:10])
    print("Overbought:", len(overbought), overbought[:10])

    print(f"\nSaved full history to {ALL_SIGNALS_PATH}")
    print(f"Saved latest signals to {LATEST_SIGNALS_PATH}")


if __name__ == "__main__":
    main()