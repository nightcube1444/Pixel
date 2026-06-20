from pathlib import Path
import pandas as pd

MARKET_DATA_PATH = Path("data/market_data.csv")
WATCHLIST_PATH = Path("data/speculative_watchlist.csv")
CROSS_ASSET_PATH = Path("data/cross_asset_pattern_recognition.csv")

OUTPUT_PATH = Path("data/candle_explanations.csv")


def safe_read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return None


def clean_ticker(ticker):
    return str(ticker).replace(".NS", "").strip().upper()


def candle_type(open_price, high, low, close):
    body = abs(close - open_price)
    candle_range = high - low

    if candle_range <= 0:
        return "UNKNOWN"

    body_pct = body / candle_range

    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low

    if close > open_price and body_pct > 0.6:
        return "STRONG_BULLISH_CANDLE"

    if close < open_price and body_pct > 0.6:
        return "STRONG_BEARISH_CANDLE"

    if body_pct < 0.2:
        return "DOJI_INDECISION"

    if lower_wick > body * 2 and close > open_price:
        return "BULLISH_REJECTION"

    if upper_wick > body * 2 and close < open_price:
        return "BEARISH_REJECTION"

    if close > open_price:
        return "BULLISH_CANDLE"

    if close < open_price:
        return "BEARISH_CANDLE"

    return "NEUTRAL_CANDLE"


def explain_candle(candle):
    explanations = {
        "STRONG_BULLISH_CANDLE": "Buyers controlled most of the session. This shows strong demand.",
        "STRONG_BEARISH_CANDLE": "Sellers controlled most of the session. This shows strong selling pressure.",
        "DOJI_INDECISION": "Open and close are close together. Buyers and sellers are undecided.",
        "BULLISH_REJECTION": "Price went lower but buyers pushed it back up. This can show support.",
        "BEARISH_REJECTION": "Price went higher but sellers pushed it back down. This can show resistance.",
        "BULLISH_CANDLE": "The stock closed above its open. Buyers had some control.",
        "BEARISH_CANDLE": "The stock closed below its open. Sellers had some control.",
        "NEUTRAL_CANDLE": "No strong candle message.",
        "UNKNOWN": "Not enough candle data.",
    }

    return explanations.get(candle, "No explanation available.")


def trend_state(df):
    if len(df) < 20:
        return "INSUFFICIENT_HISTORY"

    last_close = df["Close"].iloc[-1]
    ma5 = df["Close"].tail(5).mean()
    ma20 = df["Close"].tail(20).mean()

    if last_close > ma5 > ma20:
        return "SHORT_TERM_UPTREND"

    if last_close < ma5 < ma20:
        return "SHORT_TERM_DOWNTREND"

    return "CHOPPY_OR_SIDEWAYS"


def explain_trend(trend):
    if trend == "SHORT_TERM_UPTREND":
        return "Price is above short-term averages. Momentum is positive."

    if trend == "SHORT_TERM_DOWNTREND":
        return "Price is below short-term averages. Momentum is weak."

    if trend == "CHOPPY_OR_SIDEWAYS":
        return "Price is not trending cleanly. Signals may be noisy."

    return "Not enough history to judge trend."


def build_summary(ticker, candle, trend, signal, action, risk):
    if action == "WATCH":
        return (
            f"{ticker} is a WATCH candidate. The latest candle is {candle}, "
            f"and the trend condition is {trend}. Use paper trading only."
        )

    if action == "AVOID_FOR_NOW":
        return (
            f"{ticker} is not a clean trade right now. The latest candle is {candle}, "
            f"and Pixel marks it as AVOID_FOR_NOW."
        )

    return (
        f"{ticker} has signal {signal}. Latest candle is {candle}. "
        f"Risk level is {risk}."
    )


def main():
    market = safe_read_csv(MARKET_DATA_PATH)
    watchlist = safe_read_csv(WATCHLIST_PATH)
    cross_asset = safe_read_csv(CROSS_ASSET_PATH)

    if market is None:
        print("Missing market_data.csv")
        return

    if watchlist is None:
        print("Missing speculative_watchlist.csv")
        return

    market = market.copy()
    watchlist = watchlist.copy()

    market["CleanTicker"] = market["Ticker"].apply(clean_ticker)
    watchlist["CleanTicker"] = watchlist["Ticker"].apply(clean_ticker)

    if cross_asset is not None:
        cross_asset = cross_asset.copy()
        cross_asset["CleanTicker"] = cross_asset["Ticker"].apply(clean_ticker)

    rows = []

    for _, stock in watchlist.iterrows():
        ticker = stock["CleanTicker"]

        stock_data = market[market["CleanTicker"] == ticker].copy()

        if stock_data.empty:
            continue

        stock_data["Date"] = pd.to_datetime(stock_data["Date"], errors="coerce")
        stock_data = stock_data.dropna(subset=["Date"])
        stock_data = stock_data.sort_values("Date")

        for col in ["Open", "High", "Low", "Close"]:
            stock_data[col] = pd.to_numeric(stock_data[col], errors="coerce")

        stock_data = stock_data.dropna(subset=["Open", "High", "Low", "Close"])

        if stock_data.empty:
            continue

        latest = stock_data.iloc[-1]

        candle = candle_type(
            latest["Open"],
            latest["High"],
            latest["Low"],
            latest["Close"],
        )

        trend = trend_state(stock_data)

        signal = str(stock.get("PrimarySignal", "NONE"))
        action = str(stock.get("Action", ""))
        risk = str(stock.get("RiskLevel", ""))

        pattern_type = ""
        action_bias = ""
        risk_meaning = ""

        if cross_asset is not None:
            match = cross_asset[cross_asset["CleanTicker"] == ticker]

            if not match.empty:
                row = match.iloc[0]
                pattern_type = row.get("PatternType", "")
                action_bias = row.get("ActionBias", "")
                risk_meaning = row.get("RiskMeaning", "")

        summary = build_summary(
            ticker,
            candle,
            trend,
            signal,
            action,
            risk,
        )

        lesson = (
            f"Candle lesson: {explain_candle(candle)} "
            f"Trend lesson: {explain_trend(trend)}"
        )

        rows.append({
            "Ticker": ticker,
            "Date": str(latest["Date"].date()),
            "Open": round(float(latest["Open"]), 2),
            "High": round(float(latest["High"]), 2),
            "Low": round(float(latest["Low"]), 2),
            "Close": round(float(latest["Close"]), 2),
            "CandleType": candle,
            "CandleExplanation": explain_candle(candle),
            "TrendState": trend,
            "TrendExplanation": explain_trend(trend),
            "PrimarySignal": signal,
            "Action": action,
            "RiskLevel": risk,
            "PatternType": pattern_type,
            "ActionBias": action_bias,
            "RiskMeaning": risk_meaning,
            "Summary": summary,
            "Lesson": lesson,
        })

    result = pd.DataFrame(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print("\nCANDLE EXPLANATION ENGINE\n")
    print(result[[
        "Ticker",
        "CandleType",
        "TrendState",
        "PrimarySignal",
        "Action",
        "Summary",
    ]].to_string(index=False))

    print()
    print(f"Rows: {len(result)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()