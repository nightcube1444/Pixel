from pathlib import Path
import pandas as pd

LATEST_SIGNALS_PATH = Path("data/latest_stock_signals.csv")
LIVE_MATCHES_PATH = Path("data/live_pattern_matches.csv")
ASSET_UNIVERSE_PATH = Path("config/asset_universe.csv")

OUTPUT_PATH = Path("data/speculative_watchlist.csv")


SPECULATIVE_TICKERS = {
    "IDEA",
    "SUZLON",
    "YESBANK",
    "RVNL",
    "IRFC",
    "IREDA",
    "RKLB",
    "IRDM",
    "SOFI",
    "PLTR",
    "RIVN",
    "LCID",
    "IONQ",
    "SOUN",
}


def clean_ticker(ticker):
    return str(ticker).replace(".NS", "").strip().upper()


def safe_read_csv(path):
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return None


def classify_risk(row):
    score = float(row.get("FinalScore", 0))
    alpha = float(row.get("AlphaScore", 0))
    winrate = float(row.get("WinRate", 0))
    trades = float(row.get("Trades", 0))

    if trades < 30:
        return "VERY_HIGH"

    if score >= 60 and alpha > 0 and winrate >= 55 and trades >= 100:
        return "HIGH_BUT_INTERESTING"

    if score >= 50 and alpha > 0:
        return "HIGH"

    return "SPECULATIVE"


def decide_action(row):
    risk = row.get("RiskLevel", "")
    score = float(row.get("FinalScore", 0))
    alpha = float(row.get("AlphaScore", 0))
    winrate = float(row.get("WinRate", 0))
    trades = float(row.get("Trades", 0))

    if risk == "VERY_HIGH":
        return "PAPER_ONLY"

    if score >= 60 and alpha > 0 and winrate >= 55 and trades >= 100:
        return "WATCH_CLOSELY"

    if score >= 50 and alpha > 0:
        return "WATCH"

    return "AVOID_FOR_NOW"


def main():
    signals = safe_read_csv(LATEST_SIGNALS_PATH)
    matches = safe_read_csv(LIVE_MATCHES_PATH)
    universe = safe_read_csv(ASSET_UNIVERSE_PATH)

    if signals is None:
        print("Missing latest_stock_signals.csv. Run signal_engine.py first.")
        return

    signals = signals.copy()
    signals["CleanTicker"] = signals["Ticker"].apply(clean_ticker)

    speculative = signals[
        signals["CleanTicker"].isin(SPECULATIVE_TICKERS)
    ].copy()

    if speculative.empty:
        print("No speculative tickers found in latest signals.")
        return

    if matches is not None:
        matches = matches.copy()
        matches["CleanTicker"] = matches["Ticker"].apply(clean_ticker)

        keep_cols = [
            "CleanTicker",
            "Pattern",
            "AlphaScore",
            "WinRate",
            "Trades",
        ]

        existing_cols = [c for c in keep_cols if c in matches.columns]

        speculative = speculative.merge(
            matches[existing_cols],
            on="CleanTicker",
            how="left"
        )

    for col in ["Pattern", "AlphaScore", "WinRate", "Trades"]:
        if col not in speculative.columns:
            speculative[col] = ""

    if universe is not None:
        universe = universe.copy()
        universe["CleanTicker"] = universe["Ticker"].apply(clean_ticker)

        extra_cols = ["CleanTicker", "Market", "AssetType", "Sector"]
        existing = [c for c in extra_cols if c in universe.columns]

        speculative = speculative.merge(
            universe[existing],
            on="CleanTicker",
            how="left",
            suffixes=("", "_Universe")
        )

    speculative["RiskLevel"] = speculative.apply(classify_risk, axis=1)
    speculative["Action"] = speculative.apply(decide_action, axis=1)

    output_cols = [
        "Ticker",
        "Market",
        "AssetType",
        "Sector",
        "Close",
        "PrimarySignal",
        "MarketRegime",
        "Volatility",
        "FinalScore",
        "Pattern",
        "AlphaScore",
        "WinRate",
        "Trades",
        "RiskLevel",
        "Action",
    ]

    available_cols = [c for c in output_cols if c in speculative.columns]

    result = speculative[available_cols].copy()

    result["FinalScore"] = pd.to_numeric(result["FinalScore"], errors="coerce").fillna(0)

    if "AlphaScore" in result.columns:
        result["AlphaScore"] = pd.to_numeric(result["AlphaScore"], errors="coerce").fillna(0)

    if "WinRate" in result.columns:
        result["WinRate"] = pd.to_numeric(result["WinRate"], errors="coerce").fillna(0)

    if "Trades" in result.columns:
        result["Trades"] = pd.to_numeric(result["Trades"], errors="coerce").fillna(0)

    result = result.sort_values(
        by=["Action", "FinalScore", "AlphaScore"],
        ascending=[True, False, False]
    ).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print("\nSPECULATIVE WATCHLIST\n")
    print(result.to_string(index=False))
    print()
    print(f"Rows: {len(result)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()