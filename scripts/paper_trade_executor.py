from pathlib import Path
from datetime import datetime
import pandas as pd

SIGNALS_PATH = Path("data/latest_stock_signals.csv")
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
            "WinLoss",
            "ExitReason",
            "PatternKey",
        ])
    if "ExitReason" not in df.columns:
        df["ExitReason"] = ""
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


def update_open_positions(open_df: pd.DataFrame, signals_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
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
        exit_price = float(live_row["Close"])
        holding_bars = int(pos.get("HoldingBars", 0)) + 1
        return_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)

        current_signal = str(live_row["PrimarySignal"]).upper()
        entry_signal = str(pos["PrimarySignal"]).upper()

        exit_reason = None

        if return_pct >= TAKE_PROFIT_PCT:
            exit_reason = "TARGET_HIT"
        elif return_pct <= STOP_LOSS_PCT:
            exit_reason = "STOP_HIT"
        elif holding_bars >= MAX_HOLD_BARS:
            exit_reason = "TIME_EXIT"
        elif current_signal != entry_signal:
            exit_reason = "SIGNAL_FLIP"

        if exit_reason:
            exits.append({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Ticker": ticker,
                "PrimarySignal": entry_signal,
                "MarketRegime": pos["MarketRegime"],
                "Volatility": pos["Volatility"],
                "PriorityScore": pos["PriorityScore"],
                "EntryPrice": entry_price,
                "ExitPrice": exit_price,
                "HoldingBars": holding_bars,
                "ReturnPct": return_pct,
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

    open_df, exits = update_open_positions(open_df, signals_df)

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