from pathlib import Path
from datetime import datetime
import pandas as pd

SIGNALS_PATH = Path("data/latest_stock_signals.csv")
MARKET_DATA_PATH = Path("data/market_data.csv")
OPEN_POSITIONS_PATH = Path("data/open_paper_positions.csv")
TRADE_LOG_PATH = Path("data/paper_trade_log.csv")
SUMMARY_PATH = Path("data/paper_trade_summary.txt")

ENTRY_SIGNALS = {"PANIC", "MOMENTUM"}
MIN_SCORE = 55.0
TAKE_PROFIT_PCT = 2.0
STOP_LOSS_PCT = -2.0
MAX_HOLD_BARS = 3
MAX_OPEN_POSITIONS = 5
MAX_NEW_TRADES_PER_RUN = 2


def safe_read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return None
    if df.empty:
        return None
    return df


def ensure_open_positions_file() -> pd.DataFrame:
    df = safe_read_csv(OPEN_POSITIONS_PATH)
    if df is None:
        return pd.DataFrame(columns=[
            "Timestamp",
            "Ticker",
            "EntryPrice",
            "PrimarySignal",
            "MarketRegime",
            "Volatility",
            "PriorityScore",
            "HoldingBars",
            "PatternKey",
        ])
    return df


def ensure_trade_log_file() -> pd.DataFrame:
    df = safe_read_csv(TRADE_LOG_PATH)
    if df is None:
        return pd.DataFrame(columns=[
            "Timestamp",
            "Ticker",
            "PrimarySignal",
            "MarketRegime",
            "Volatility",
            "PriorityScore",
            "EntryPrice",
            "ExitPrice",
            "HoldingBars",
            "ReturnPct",
            "RawClose",
            "RawReturnPct",
            "WinLoss",
            "ExitReason",
            "PatternKey",
        ])
    if "ExitReason" not in df.columns:
        df["ExitReason"] = ""
    if "RawClose" not in df.columns:
        df["RawClose"] = df.get("ExitPrice", "")
    if "RawReturnPct" not in df.columns:
        df["RawReturnPct"] = df.get("ReturnPct", "")
    return df


def build_pattern_key(row: pd.Series) -> str:
    ticker = str(row.get("Ticker", "")).strip().upper()
    signal = str(row.get("PrimarySignal", "")).strip().upper()
    regime = str(row.get("MarketRegime", "")).strip().upper()
    vol = str(row.get("Volatility", "")).strip().upper()
    return f"{ticker}|{signal}|{regime}|{vol}"


def load_latest_signals() -> pd.DataFrame:
    df = safe_read_csv(SIGNALS_PATH)
    if df is None:
        raise ValueError("latest_stock_signals.csv is missing or empty.")

    required = ["Ticker", "Close", "PrimarySignal", "MarketRegime", "Volatility", "FinalScore"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required signal columns: {missing}")

    df = df.copy()
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df["PrimarySignal"] = df["PrimarySignal"].astype(str).str.strip().str.upper()
    df["MarketRegime"] = df["MarketRegime"].astype(str).str.strip().str.upper()
    df["Volatility"] = df["Volatility"].astype(str).str.strip().str.upper()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["FinalScore"] = pd.to_numeric(df["FinalScore"], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["Ticker", "Close"]).copy()
    df["PatternKey"] = df.apply(build_pattern_key, axis=1)

    return df


def load_market_ohlc() -> pd.DataFrame:
    """Load Ticker/Date/High/Low so exits can detect an intrabar touch of the
    target or stop level, instead of only comparing against the latest Close.
    Returns an empty frame (not an error) if market_data.csv is unavailable,
    since the executor can still fall back to Close-only behavior."""
    df = safe_read_csv(MARKET_DATA_PATH)
    if df is None:
        return pd.DataFrame(columns=["Ticker", "Date", "High", "Low"])

    required = ["Ticker", "Date", "High", "Low"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return pd.DataFrame(columns=["Ticker", "Date", "High", "Low"])

    df = df.copy()
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df["DateObj"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Date"] = df["DateObj"].dt.strftime("%Y-%m-%d")
    df["High"] = pd.to_numeric(df["High"], errors="coerce")
    df["Low"] = pd.to_numeric(df["Low"], errors="coerce")

    return df.dropna(subset=["Ticker", "Date"])[["Ticker", "Date", "DateObj", "High", "Low"]]


def build_ohlc_lookups(ohlc_df: pd.DataFrame) -> tuple[dict, dict]:
    """Build two lookups: an exact (Ticker, Date) -> (High, Low) map for the
    bar matching today's signal snapshot, and a fallback latest-bar-per-ticker
    map for when the exact date isn't present yet."""
    if ohlc_df.empty:
        return {}, {}

    exact = {
        (r["Ticker"], r["Date"]): (r["High"], r["Low"])
        for _, r in ohlc_df.iterrows()
    }

    latest = (
        ohlc_df.sort_values("DateObj")
        .groupby("Ticker")
        .tail(1)
        .set_index("Ticker")[["High", "Low"]]
        .apply(tuple, axis=1)
        .to_dict()
    )

    return exact, latest


def choose_entries(signals_df: pd.DataFrame, open_df: pd.DataFrame) -> pd.DataFrame:
    open_tickers = set(open_df["Ticker"].astype(str).str.upper()) if not open_df.empty else set()

    candidates = signals_df[
        (signals_df["PrimarySignal"].isin(ENTRY_SIGNALS)) &
        (signals_df["FinalScore"] >= MIN_SCORE)
    ].copy()

    candidates = candidates[~candidates["Ticker"].isin(open_tickers)].copy()

    if candidates.empty:
        return candidates

    remaining_slots = max(0, MAX_OPEN_POSITIONS - len(open_df))
    limit = min(MAX_NEW_TRADES_PER_RUN, remaining_slots)

    if limit <= 0:
        return candidates.iloc[0:0].copy()

    candidates["PriorityScore"] = candidates["FinalScore"]
    candidates = candidates.sort_values(
        by=["FinalScore", "Ticker"],
        ascending=[False, True]
    )

    return candidates.head(limit)


def update_open_positions(
    open_df: pd.DataFrame,
    signals_df: pd.DataFrame,
    exact_ohlc: dict,
    latest_ohlc: dict,
) -> tuple[pd.DataFrame, list[dict]]:
    exits = []
    latest_map = {row["Ticker"]: row for _, row in signals_df.iterrows()}
    remaining_rows = []

    for _, pos in open_df.iterrows():
        ticker = str(pos["Ticker"]).upper()

        if ticker not in latest_map:
            remaining_rows.append(pos.to_dict())
            continue

        live_row = latest_map[ticker]
        entry_price = float(pos["EntryPrice"])
        close_price = float(live_row["Close"])
        signal_date = str(live_row.get("Date", ""))
        holding_bars = int(pos.get("HoldingBars", 0)) + 1

        # Prefer the exact day's High/Low so a target/stop that was only
        # touched intrabar still counts, instead of requiring the Close
        # itself to land beyond the threshold. Fall back to Close if no
        # OHLC bar is available for this ticker/date.
        day_high, day_low = exact_ohlc.get((ticker, signal_date), (None, None))
        if day_high is None or day_low is None or pd.isna(day_high) or pd.isna(day_low):
            day_high, day_low = latest_ohlc.get(ticker, (close_price, close_price))
        if pd.isna(day_high) or pd.isna(day_low):
            day_high, day_low = close_price, close_price

        target_price = entry_price * (1 + TAKE_PROFIT_PCT / 100)
        stop_price = entry_price * (1 + STOP_LOSS_PCT / 100)

        hit_target = day_high >= target_price
        hit_stop = day_low <= stop_price

        current_signal = str(live_row["PrimarySignal"]).upper()
        entry_signal = str(pos["PrimarySignal"]).upper()

        exit_reason = None
        fill_price = close_price

        if hit_target and hit_stop:
            # Daily OHLC can't tell us which level was touched first, so we
            # assume the worse outcome (stop) rather than overstate results.
            exit_reason = "STOP_HIT"
            fill_price = stop_price
        elif hit_stop:
            exit_reason = "STOP_HIT"
            fill_price = stop_price
        elif hit_target:
            exit_reason = "TARGET_HIT"
            fill_price = target_price
        elif holding_bars >= MAX_HOLD_BARS:
            exit_reason = "TIME_EXIT"
            fill_price = close_price
        elif current_signal != entry_signal:
            exit_reason = "SIGNAL_FLIP"
            fill_price = close_price

        if exit_reason:
            return_pct = round(((fill_price - entry_price) / entry_price) * 100, 2)
            raw_return_pct = round(((close_price - entry_price) / entry_price) * 100, 2)

            exits.append({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Ticker": ticker,
                "PrimarySignal": entry_signal,
                "MarketRegime": pos["MarketRegime"],
                "Volatility": pos["Volatility"],
                "PriorityScore": pos["PriorityScore"],
                "EntryPrice": entry_price,
                "ExitPrice": fill_price,
                "HoldingBars": holding_bars,
                "ReturnPct": return_pct,
                "RawClose": close_price,
                "RawReturnPct": raw_return_pct,
                "WinLoss": "WIN" if return_pct > 0 else "LOSS",
                "ExitReason": exit_reason,
                "PatternKey": pos["PatternKey"],
            })
        else:
            updated = pos.to_dict()
            updated["HoldingBars"] = holding_bars
            remaining_rows.append(updated)

    remaining_df = pd.DataFrame(
        remaining_rows,
        columns=[
            "Timestamp",
            "Ticker",
            "EntryPrice",
            "PrimarySignal",
            "MarketRegime",
            "Volatility",
            "PriorityScore",
            "HoldingBars",
            "PatternKey",
        ],
    )

    return remaining_df, exits


def create_new_positions(entries_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in entries_df.iterrows():
        rows.append({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Ticker": row["Ticker"],
            "EntryPrice": float(row["Close"]),
            "PrimarySignal": row["PrimarySignal"],
            "MarketRegime": row["MarketRegime"],
            "Volatility": row["Volatility"],
            "PriorityScore": round(float(row["FinalScore"]), 2),
            "HoldingBars": 0,
            "PatternKey": row["PatternKey"],
        })

    return pd.DataFrame(rows)


def main() -> None:
    signals_df = load_latest_signals()
    open_df = ensure_open_positions_file()
    trade_log_df = ensure_trade_log_file()

    ohlc_df = load_market_ohlc()
    exact_ohlc, latest_ohlc = build_ohlc_lookups(ohlc_df)

    open_df, exits = update_open_positions(open_df, signals_df, exact_ohlc, latest_ohlc)

    entries_df = choose_entries(signals_df, open_df)
    new_open_df = create_new_positions(entries_df)

    if not new_open_df.empty:
        open_df = pd.concat([open_df, new_open_df], ignore_index=True)

    if exits:
        exits_df = pd.DataFrame(exits)
        trade_log_df = pd.concat([trade_log_df, exits_df], ignore_index=True)

    OPEN_POSITIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRADE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    open_df.to_csv(OPEN_POSITIONS_PATH, index=False)
    trade_log_df.to_csv(TRADE_LOG_PATH, index=False)

    open_tickers = ", ".join(open_df["Ticker"].astype(str).tolist()) if not open_df.empty else "None"

    summary_lines = [
        "MINI CUBE PAPER TRADE EXECUTOR",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"New entries: {len(new_open_df)}",
        f"Closed trades: {len(exits)}",
        f"Open positions: {len(open_df)}",
        "",
        "Open Tickers:",
        open_tickers,
    ]

    SUMMARY_PATH.write_text("\n".join(summary_lines), encoding="utf-8")
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()