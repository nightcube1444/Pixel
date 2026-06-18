from pathlib import Path
from datetime import datetime
import pandas as pd

# =========================
# Paths
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

SIGNAL_SOURCE_CANDIDATES = [
    BASE_DIR / "data/latest_stock_signals.csv",
    BASE_DIR / "data/alpha_ranking_results.csv",
    BASE_DIR / "data/all_stock_signals_with_context.csv",
    BASE_DIR / "data/all_stock_signals.csv",
    BASE_DIR / "data/live_signal_log.csv",
]

SUMMARY_PATH = BASE_DIR / "data/live_monitor_summary.txt"
STATE_PATH = BASE_DIR / "data/live_monitor_state.csv"
STATE_LOG_PATH = BASE_DIR / "data/mini_cube_state_log.csv"


# =========================
# Helpers
# =========================
def safe_read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if path.stat().st_size == 0:
        return None

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return None

    if df.empty:
        return None

    return df


def load_signal_source() -> tuple[pd.DataFrame | None, str | None]:
    for path in SIGNAL_SOURCE_CANDIDATES:
        df = safe_read_csv(path)
        if df is not None:
            return df, path.name
    return None, None


def clean_text(value, default: str = "NONE") -> str:
    if pd.isna(value):
        return default

    text = str(value).strip()

    if text == "" or text.lower() == "nan":
        return default

    return text


# =========================
# Scoring for top signal
# =========================
def compute_priority_score(row) -> int:
    score = 0

    primary_signal = clean_text(row.get("PrimarySignal", "NONE"))
    market_regime = clean_text(row.get("MarketRegime", "UNKNOWN"), default="UNKNOWN")
    volatility = clean_text(row.get("Volatility", "NONE"))

    if primary_signal == "PANIC":
        score += 50
    elif primary_signal == "MOMENTUM":
        score += 40
    elif primary_signal == "VOLATILE":
        score += 30
    elif primary_signal == "OVERSOLD":
        score += 20
    elif primary_signal == "OVERBOUGHT":
        score += 10

    if market_regime == "HIGH_VOLATILITY":
        score += 15
    elif market_regime == "BEAR":
        score += 10
    elif market_regime == "BULL":
        score += 8
    elif market_regime == "SIDEWAYS":
        score += 5

    if volatility == "VOLATILE":
        score += 10

    return score


def pick_top_signal(df: pd.DataFrame) -> dict | None:

    working = df.copy()

    # -------------------------
    # Alpha ranking file
    # -------------------------
    if "Pattern" in working.columns:

        if "AlphaScore" in working.columns:
            working["Score"] = pd.to_numeric(
                working["AlphaScore"],
                errors="coerce"
            ).fillna(0)

        else:
            working["Score"] = 0

        if "Trades" not in working.columns:

            if "TimesSeen" in working.columns:
                working["Trades"] = pd.to_numeric(
                    working["TimesSeen"],
                    errors="coerce"
                ).fillna(0)

            else:
                working["Trades"] = 0

        working = working.sort_values(
            by=["Score", "Trades"],
            ascending=[False, False]
        )

        if working.empty:
            return None

        row = working.iloc[0]

        return {
            "Ticker": row["Pattern"],
            "PrimarySignal": "PATTERN",
            "MarketRegime": "ALPHA",
            "Volatility": "NONE",
            "Trades": int(row["Trades"]),
            "Score": float(row["Score"]),
            "PriorityScore": int(float(row["Score"]))
        }

    # -------------------------
    # Stock signal file
    # -------------------------
    expected_columns = [
        "Ticker",
        "PrimarySignal",
        "MarketRegime",
        "Volatility"
    ]

    missing_columns = [
        c for c in expected_columns
        if c not in working.columns
    ]

    if missing_columns:
        print(
            f"Warning: Missing columns: {missing_columns}"
        )

    if "FinalScore" in working.columns:
        working["Score"] = pd.to_numeric(
            working["FinalScore"],
            errors="coerce"
        ).fillna(0)

    elif "Score" in working.columns:
        working["Score"] = pd.to_numeric(
            working["Score"],
            errors="coerce"
        ).fillna(0)

    else:
        working["Score"] = 0

    if "Trades" not in working.columns:
        working["Trades"] = 0

    if "PrimarySignal" not in working.columns:
        working["PrimarySignal"] = "NONE"

    if "MarketRegime" not in working.columns:
        working["MarketRegime"] = "UNKNOWN"

    if "Volatility" not in working.columns:
        working["Volatility"] = "NONE"

    working["Trades"] = pd.to_numeric(
        working["Trades"],
        errors="coerce"
    ).fillna(0)

    working["PriorityScore"] = working.apply(
        compute_priority_score,
        axis=1
    )

    working = working.sort_values(
        by=[
            "PriorityScore",
            "Score",
            "Trades"
        ],
        ascending=[
            False,
            False,
            False
        ]
    )

    if working.empty:
        return None

    row = working.iloc[0]

    return {
        "Ticker": clean_text(
            row.get("Ticker", "UNKNOWN")
        ),
        "PrimarySignal": clean_text(
            row.get("PrimarySignal", "NONE")
        ),
        "MarketRegime": clean_text(
            row.get("MarketRegime", "UNKNOWN")
        ),
        "Volatility": clean_text(
            row.get("Volatility", "NONE")
        ),
        "Trades": int(row.get("Trades", 0)),
        "Score": float(row.get("Score", 0)),
        "PriorityScore": int(
            row.get("PriorityScore", 0)
        ),
    }

# =========================
# Market state and groups
# =========================
def get_market_state(df: pd.DataFrame) -> str:
    if "MarketRegime" not in df.columns:
        return "UNKNOWN"

    latest = df["MarketRegime"].dropna().astype(str).str.strip()
    if latest.empty:
        return "UNKNOWN"

    counts = latest.value_counts()
    return counts.index[0]


def extract_category_list(df: pd.DataFrame, column: str, match_value: str) -> list[str]:
    if column not in df.columns or "Ticker" not in df.columns:
        return []

    series = df[column].fillna("").astype(str).str.strip().str.upper()
    filtered = df[series == match_value.upper()]
    tickers = filtered["Ticker"].dropna().astype(str).str.strip().unique().tolist()
    return sorted(tickers)


def extract_regime_list(df: pd.DataFrame, regime: str) -> list[str]:
    if "MarketRegime" not in df.columns or "Ticker" not in df.columns:
        return []

    series = df["MarketRegime"].fillna("").astype(str).str.strip().str.upper()
    filtered = df[series == regime.upper()]
    tickers = filtered["Ticker"].dropna().astype(str).str.strip().unique().tolist()
    return sorted(tickers)


def format_list(items: list[str], max_items: int = 10) -> str:
    if not items:
        return "None"
    return ", ".join(items[:max_items])


# =========================
# Summary
# =========================
def build_summary(
    source_name: str,
    market_state: str,
    top_signal: dict | None,
    bull: list[str],
    bear: list[str],
    sideways: list[str],
    high_volatility: list[str],
    panic: list[str],
    momentum: list[str],
    oversold: list[str],
    overbought: list[str],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if top_signal is None:
        top_line = "Top Signal: NONE"
    else:
        top_line = (
            f"Top Signal: {top_signal['Ticker']} | "
            f"{top_signal['PrimarySignal']}|{top_signal['MarketRegime']}|{top_signal['Volatility']} | "
            f"Trades={top_signal['Trades']} | Score={top_signal['Score']:.3f} | "
            f"Priority={top_signal['PriorityScore']}"
        )

    lines = [
        "MINI CUBE LIVE MONITOR",
        f"Time: {now}",
        f"Source: {source_name}",
        "",
        f"Market State: {market_state}",
        "",
        top_line,
        "",
        f"Bull: {format_list(bull)}",
        f"Bear: {format_list(bear)}",
        f"Sideways: {format_list(sideways)}",
        f"High Volatility: {format_list(high_volatility)}",
        f"Panic: {format_list(panic)}",
        f"Momentum: {format_list(momentum)}",
        f"Oversold: {format_list(oversold)}",
        f"Overbought: {format_list(overbought)}",
    ]

    return "\n".join(lines)


# =========================
# Save helpers
# =========================
def save_state_snapshot(row: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(STATE_PATH, index=False)


def build_state_row(
    source_name: str,
    market_state: str,
    top_signal: dict | None,
    bull: list[str],
    bear: list[str],
    sideways: list[str],
    high_volatility: list[str],
    panic: list[str],
    momentum: list[str],
    oversold: list[str],
    overbought: list[str],
) -> dict:
    return {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "MarketState": market_state,
        "TopTicker": top_signal["Ticker"] if top_signal else "NONE",
        "TopPrimarySignal": top_signal["PrimarySignal"] if top_signal else "NONE",
        "TopMarketRegime": top_signal["MarketRegime"] if top_signal else "UNKNOWN",
        "TopVolatility": top_signal["Volatility"] if top_signal else "NONE",
        "TopScore": round(float(top_signal["Score"]), 3) if top_signal else 0.0,
        "TopPriorityScore": int(top_signal["PriorityScore"]) if top_signal else 0,
        "BullCount": len(bull),
        "BearCount": len(bear),
        "SidewaysCount": len(sideways),
        "HighVolCount": len(high_volatility),
        "PanicCount": len(panic),
        "MomentumCount": len(momentum),
        "OversoldCount": len(oversold),
        "OverboughtCount": len(overbought),
        "SourceFile": source_name,
    }


def has_state_changed(new_row: dict) -> bool:
    if not STATE_LOG_PATH.exists():
        return True

    try:
        old_df = pd.read_csv(STATE_LOG_PATH)
    except Exception:
        return True

    if old_df.empty:
        return True

    last_row = old_df.iloc[-1].to_dict()

    keys_to_compare = [
        "MarketState",
        "TopTicker",
        "TopPrimarySignal",
        "TopMarketRegime",
        "TopVolatility",
        "TopScore",
        "TopPriorityScore",
        "BullCount",
        "BearCount",
        "SidewaysCount",
        "HighVolCount",
        "PanicCount",
        "MomentumCount",
        "OversoldCount",
        "OverboughtCount",
    ]

    for key in keys_to_compare:
        old_value = str(last_row.get(key, "")).strip()
        new_value = str(new_row.get(key, "")).strip()

        if old_value != new_value:
            return True

    return False


def append_state_log_if_changed(row: dict) -> bool:
    out_df = pd.DataFrame([row])
    STATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not STATE_LOG_PATH.exists():
        out_df.to_csv(STATE_LOG_PATH, index=False)
        return True

    if has_state_changed(row):
        out_df.to_csv(STATE_LOG_PATH, mode="a", header=False, index=False)
        return True

    return False

def extract_primary_signal_list(df: pd.DataFrame, signal_name: str) -> list[str]:

    if "PrimarySignal" not in df.columns:
        return []

    filtered = df[
        df["PrimarySignal"]
        .fillna("")
        .astype(str)
        .str.upper()
        == signal_name.upper()
    ]

    return sorted(
        filtered["Ticker"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


# =========================
# Main
# =========================
def main() -> None:
    df, source_name = load_signal_source()

    if df is None or source_name is None:
        print("No usable signal file found.")
        return

    market_state = get_market_state(df)
    top_signal = pick_top_signal(df)

    bull = extract_regime_list(df, "BULL")
    bear = extract_regime_list(df, "BEAR")
    sideways = extract_regime_list(df, "SIDEWAYS")
    high_volatility = extract_regime_list(df, "HIGH_VOLATILITY")

    panic = extract_primary_signal_list(df, "PANIC")
    momentum = extract_primary_signal_list(df, "MOMENTUM")
    oversold = extract_primary_signal_list(df, "OVERSOLD")
    overbought = extract_primary_signal_list(df, "OVERBOUGHT")

    summary = build_summary(
        source_name=source_name,
        market_state=market_state,
        top_signal=top_signal,
        bull=bull,
        bear=bear,
        sideways=sideways,
        high_volatility=high_volatility,
        panic=panic,
        momentum=momentum,
        oversold=oversold,
        overbought=overbought,
    )

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    state_row = build_state_row(
        source_name=source_name,
        market_state=market_state,
        top_signal=top_signal,
        bull=bull,
        bear=bear,
        sideways=sideways,
        high_volatility=high_volatility,
        panic=panic,
        momentum=momentum,
        oversold=oversold,
        overbought=overbought,
    )

    save_state_snapshot(state_row)
    logged = append_state_log_if_changed(state_row)

    print(summary)
    print(f"\nSaved live summary to {SUMMARY_PATH}")
    print(f"Saved state snapshot to {STATE_PATH}")

    if logged:
        print(f"State changed. Appended row to {STATE_LOG_PATH}")
    else:
        print("No important state change. Log not updated.")


if __name__ == "__main__":
    main()