from pathlib import Path
import pandas as pd

LIVE_PATTERNS_PATH = Path("data/live_pattern_matches.csv")
LATEST_SIGNALS_PATH = Path("data/latest_stock_signals.csv")
BOUNCE_RANKINGS_PATH = Path("data/bounce_pattern_rankings.csv")
LIQUIDITY_PATH = Path("data/liquidity_report.csv")

OUTPUT_PATH = Path("data/bounce_opportunities.csv")
DIAGNOSTIC_PATH = Path("data/bounce_opportunity_diagnostics.csv")

MIN_EVENTS = 30
MIN_RECOVERY_RATE_10D = 55.0
MIN_AVG_BOUNCE_10D = 1.0
MIN_FINAL_SCORE = 45.0


def safe_read(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return pd.DataFrame()


def pattern_family(pattern: str) -> str:
    parts = str(pattern).split("|")
    if len(parts) < 3:
        return ""
    return "|".join(parts[:3])


def main():
    print("\nBOUNCE OPPORTUNITY ENGINE\n")

    live_df = safe_read(LIVE_PATTERNS_PATH)
    signals_df = safe_read(LATEST_SIGNALS_PATH)
    bounce_df = safe_read(BOUNCE_RANKINGS_PATH)
    liquidity_df = safe_read(LIQUIDITY_PATH)

    if live_df.empty:
        print("Missing live_pattern_matches.csv")
        return

    if signals_df.empty:
        print("Missing latest_stock_signals.csv")
        return

    if bounce_df.empty:
        print("Missing bounce_pattern_rankings.csv")
        return

    live_df["Ticker"] = live_df["Ticker"].astype(str).str.strip().str.upper()
    live_df["Pattern"] = live_df["Pattern"].astype(str).str.strip()
    live_df["PatternFamily"] = live_df["Pattern"].apply(pattern_family)

    signals_df["Ticker"] = signals_df["Ticker"].astype(str).str.strip().str.upper()
    signals_df["FinalScore"] = pd.to_numeric(
        signals_df["FinalScore"],
        errors="coerce",
    ).fillna(0)

    signals_df["PrimarySignal"] = (
        signals_df["PrimarySignal"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    bounce_df["CrossAssetPattern"] = (
        bounce_df["CrossAssetPattern"]
        .astype(str)
        .str.strip()
    )

    bounce_df["PatternFamily"] = (
        bounce_df["CrossAssetPattern"]
        .apply(pattern_family)
    )

    for col in [
        "Events",
        "AvgBounce5D",
        "AvgBounce10D",
        "RecoveryRate5D",
        "RecoveryRate10D",
        "BounceScore",
    ]:
        bounce_df[col] = pd.to_numeric(
            bounce_df[col],
            errors="coerce",
        ).fillna(0)

    family_bounce = (
        bounce_df.groupby("PatternFamily")
        .agg(
            FamilyEvents=("Events", "sum"),
            FamilyAvgBounce5D=("AvgBounce5D", "mean"),
            FamilyAvgBounce10D=("AvgBounce10D", "mean"),
            FamilyRecoveryRate5D=("RecoveryRate5D", "mean"),
            FamilyRecoveryRate10D=("RecoveryRate10D", "mean"),
            FamilyBounceScore=("BounceScore", "mean"),
        )
        .reset_index()
    )

    merged = live_df.merge(
        signals_df[
            [
                "Ticker",
                "PrimarySignal",
                "FinalScore",
                "Close",
            ]
        ],
        on="Ticker",
        how="left",
    )

    merged = merged.merge(
        bounce_df[
            [
                "CrossAssetPattern",
                "Events",
                "AvgBounce5D",
                "RecoveryRate5D",
                "AvgBounce10D",
                "RecoveryRate10D",
                "BounceScore",
            ]
        ],
        left_on="Pattern",
        right_on="CrossAssetPattern",
        how="left",
    )

    merged = merged.merge(
        family_bounce,
        on="PatternFamily",
        how="left",
    )

    if not liquidity_df.empty:
        liquidity_df["Ticker"] = (
            liquidity_df["Ticker"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        liquidity_df["LiquidityStatus"] = (
            liquidity_df["LiquidityStatus"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        merged = merged.merge(
            liquidity_df[
                [
                    "Ticker",
                    "LiquidityStatus",
                ]
            ],
            on="Ticker",
            how="left",
        )
    else:
        merged["LiquidityStatus"] = "UNKNOWN"

    for col in [
        "Events",
        "AvgBounce5D",
        "AvgBounce10D",
        "RecoveryRate5D",
        "RecoveryRate10D",
        "BounceScore",
        "FamilyEvents",
        "FamilyAvgBounce5D",
        "FamilyAvgBounce10D",
        "FamilyRecoveryRate5D",
        "FamilyRecoveryRate10D",
        "FamilyBounceScore",
        "FinalScore",
    ]:
        merged[col] = pd.to_numeric(
            merged[col],
            errors="coerce",
        ).fillna(0)

    merged["UsedBounceSource"] = "NONE"

    merged["UsedEvents"] = merged["Events"]
    merged["UsedAvgBounce5D"] = merged["AvgBounce5D"]
    merged["UsedRecoveryRate5D"] = merged["RecoveryRate5D"]
    merged["UsedAvgBounce10D"] = merged["AvgBounce10D"]
    merged["UsedRecoveryRate10D"] = merged["RecoveryRate10D"]
    merged["UsedBounceScore"] = merged["BounceScore"]

    exact_mask = merged["Events"] >= MIN_EVENTS

    merged.loc[exact_mask, "UsedBounceSource"] = "EXACT_PATTERN"

    family_mask = (
        ~exact_mask
        &
        (merged["FamilyEvents"] >= MIN_EVENTS)
    )

    merged.loc[family_mask, "UsedBounceSource"] = "PATTERN_FAMILY"
    merged.loc[family_mask, "UsedEvents"] = merged.loc[
        family_mask,
        "FamilyEvents",
    ]
    merged.loc[family_mask, "UsedAvgBounce5D"] = merged.loc[
        family_mask,
        "FamilyAvgBounce5D",
    ]
    merged.loc[family_mask, "UsedRecoveryRate5D"] = merged.loc[
        family_mask,
        "FamilyRecoveryRate5D",
    ]
    merged.loc[family_mask, "UsedAvgBounce10D"] = merged.loc[
        family_mask,
        "FamilyAvgBounce10D",
    ]
    merged.loc[family_mask, "UsedRecoveryRate10D"] = merged.loc[
        family_mask,
        "FamilyRecoveryRate10D",
    ]
    merged.loc[family_mask, "UsedBounceScore"] = merged.loc[
        family_mask,
        "FamilyBounceScore",
    ]

    merged["PassEvents"] = merged["UsedEvents"] >= MIN_EVENTS
    merged["PassRecovery"] = (
        merged["UsedRecoveryRate10D"] >= MIN_RECOVERY_RATE_10D
    )
    merged["PassAvgBounce"] = (
        merged["UsedAvgBounce10D"] >= MIN_AVG_BOUNCE_10D
    )
    merged["PassScore"] = merged["FinalScore"] >= MIN_FINAL_SCORE
    merged["PassLiquidity"] = merged["LiquidityStatus"] == "LIQUID"

    merged.to_csv(DIAGNOSTIC_PATH, index=False)

    print("\nDEBUG COUNTS\n")
    print("Total live matches:", len(merged))
    print("Exact pattern bounce matches:", int(exact_mask.sum()))
    print("Family bounce matches:", int(family_mask.sum()))
    print("Pass events:", int(merged["PassEvents"].sum()))
    print("Pass recovery:", int(merged["PassRecovery"].sum()))
    print("Pass avg bounce:", int(merged["PassAvgBounce"].sum()))
    print("Pass final score:", int(merged["PassScore"].sum()))
    print("Pass liquidity:", int(merged["PassLiquidity"].sum()))

    candidates = merged[
        merged["PassEvents"]
        &
        merged["PassRecovery"]
        &
        merged["PassAvgBounce"]
        &
        merged["PassScore"]
        &
        merged["PassLiquidity"]
    ].copy()

    if candidates.empty:
        print("\nNo bounce opportunities found.")
        print(f"Diagnostics saved -> {DIAGNOSTIC_PATH}")
        return

    candidates["BounceOpportunityScore"] = (
        candidates["FinalScore"] * 0.30
        +
        candidates["UsedBounceScore"] * 0.40
        +
        candidates["UsedRecoveryRate10D"] * 0.20
        +
        candidates["UsedAvgBounce10D"] * 2 * 0.10
    ).round(2)

    candidates["BounceDecision"] = candidates[
        "BounceOpportunityScore"
    ].apply(
        lambda x:
        "HIGH_PRIORITY"
        if x >= 80
        else
        "WATCH"
        if x >= 60
        else
        "LOW_PRIORITY"
    )

    keep_cols = [
        "Ticker",
        "PrimarySignal",
        "FinalScore",
        "Close",
        "Pattern",
        "PatternFamily",
        "UsedBounceSource",
        "UsedEvents",
        "UsedAvgBounce5D",
        "UsedRecoveryRate5D",
        "UsedAvgBounce10D",
        "UsedRecoveryRate10D",
        "UsedBounceScore",
        "BounceOpportunityScore",
        "BounceDecision",
        "LiquidityStatus",
    ]

    output = candidates[keep_cols].sort_values(
        by=[
            "BounceOpportunityScore",
            "UsedRecoveryRate10D",
            "UsedAvgBounce10D",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nBOUNCE OPPORTUNITIES\n")
    print(output.to_string(index=False))
    print(f"\nBounce Opportunities: {len(output)}")
    print(f"Saved -> {OUTPUT_PATH}")
    print(f"Diagnostics saved -> {DIAGNOSTIC_PATH}")


if __name__ == "__main__":
    main()