from pathlib import Path
import pandas as pd

SIGNALS_PATH = Path("data/latest_stock_signals.csv")
LIVE_PATTERNS_PATH = Path("data/live_pattern_matches.csv")
FAMILY_STATS_PATH = Path("data/pattern_family_stats.csv")
LIQUIDITY_PATH = Path("data/liquidity_report.csv")
OUTPUT_PATH = Path("data/family_trade_candidates.csv")

MIN_SCORE = 45
MIN_FAMILY_SCORE = 50
MIN_EVENTS = 50
ENTRY_SIGNALS = {"PANIC", "MOMENTUM"}


def safe_read(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def pattern_family(pattern: str) -> str:
    parts = str(pattern).split("|")
    if len(parts) < 3:
        return ""
    return "|".join(parts[:3])


def main():
    print("\nPATTERN FAMILY EXECUTOR\n")

    signals = safe_read(SIGNALS_PATH)
    live = safe_read(LIVE_PATTERNS_PATH)
    families = safe_read(FAMILY_STATS_PATH)
    liquidity = safe_read(LIQUIDITY_PATH)

    if signals.empty or live.empty or families.empty:
        print("Missing required input files.")
        return

    signals["Ticker"] = signals["Ticker"].astype(str).str.strip().str.upper()
    signals["PrimarySignal"] = signals["PrimarySignal"].astype(str).str.strip().str.upper()
    signals["FinalScore"] = pd.to_numeric(signals["FinalScore"], errors="coerce").fillna(0)

    live["Ticker"] = live["Ticker"].astype(str).str.strip().str.upper()
    live["Pattern"] = live["Pattern"].astype(str).str.strip()

    families["PatternFamily"] = families["PatternFamily"].astype(str).str.strip()
    families["FamilyScore"] = pd.to_numeric(families["FamilyScore"], errors="coerce").fillna(0)
    families["TotalEvents"] = pd.to_numeric(families["TotalEvents"], errors="coerce").fillna(0)

    merged = signals.merge(
        live[["Ticker", "Pattern"]],
        on="Ticker",
        how="left",
    )

    merged["Pattern"] = merged["Pattern"].fillna("").astype(str).str.strip()
    merged["PatternFamily"] = merged["Pattern"].apply(pattern_family)

    merged = merged.merge(
        families,
        on="PatternFamily",
        how="left",
    )

    if not liquidity.empty:
        liquidity["Ticker"] = liquidity["Ticker"].astype(str).str.strip().str.upper()
        liquidity["LiquidityStatus"] = liquidity["LiquidityStatus"].astype(str).str.strip().str.upper()

        liquid = set(
            liquidity[liquidity["LiquidityStatus"] == "LIQUID"]["Ticker"]
        )
    else:
        liquid = set()

    candidates = merged[
        (merged["PrimarySignal"].isin(ENTRY_SIGNALS))
        &
        (merged["FinalScore"] >= MIN_SCORE)
        &
        (merged["FamilyScore"] >= MIN_FAMILY_SCORE)
        &
        (merged["TotalEvents"] >= MIN_EVENTS)
        &
        (merged["Ticker"].isin(liquid))
    ].copy()

    if candidates.empty:
        print("No family-based candidates found.")
        return

    candidates["CombinedScore"] = (
        candidates["FinalScore"] * 0.45
        +
        candidates["FamilyScore"] * 0.55
    ).round(2)

    candidates = candidates.sort_values(
        by=["CombinedScore", "FamilyScore", "FinalScore"],
        ascending=[False, False, False],
    )

    keep_cols = [
        "Ticker",
        "PrimarySignal",
        "FinalScore",
        "Pattern",
        "PatternFamily",
        "FamilyScore",
        "FamilyStrength",
        "Members",
        "TotalEvents",
        "AvgWinRate",
        "AvgReturn10D",
        "CombinedScore",
    ]

    out = candidates[keep_cols].copy()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print(out.to_string(index=False))
    print(f"\nFamily Candidates: {len(out)}")
    print(f"Saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()