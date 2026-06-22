from pathlib import Path
import pandas as pd

SIGNALS_PATH = Path("data/latest_stock_signals.csv")
LIVE_PATTERNS_PATH = Path("data/live_pattern_matches.csv")
INSTITUTIONAL_PATH = Path("data/institutional_opportunities.csv")
EVENT_PATH = Path("data/pattern_event_validation_results.csv")
FAMILY_PATH = Path("data/pattern_family_stats.csv")
LIQUIDITY_PATH = Path("data/liquidity_report.csv")
OUTPUT_PATH = Path("data/master_opportunity_scores.csv")

MIN_MASTER_SCORE = 60


def safe_read(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return pd.DataFrame()


def normalize_ticker(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty and "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def pattern_family(pattern: str) -> str:
    parts = str(pattern).split("|")
    if len(parts) < 3:
        return ""
    return "|".join(parts[:3])


def main():
    print("\nMASTER OPPORTUNITY SCORE ENGINE\n")

    signals = normalize_ticker(safe_read(SIGNALS_PATH))
    live = normalize_ticker(safe_read(LIVE_PATTERNS_PATH))
    institutional = normalize_ticker(safe_read(INSTITUTIONAL_PATH))
    events = normalize_ticker(safe_read(EVENT_PATH))
    families = safe_read(FAMILY_PATH)
    liquidity = normalize_ticker(safe_read(LIQUIDITY_PATH))

    if signals.empty:
        print("Missing latest_stock_signals.csv")
        return

    signals["PrimarySignal"] = signals["PrimarySignal"].astype(str).str.strip().str.upper()
    signals["FinalScore"] = pd.to_numeric(signals["FinalScore"], errors="coerce").fillna(0)

    if not live.empty:
        live["Pattern"] = live["Pattern"].astype(str).str.strip()
        live["AlphaScore"] = pd.to_numeric(live.get("AlphaScore", 0), errors="coerce").fillna(0)
        live["ConfidenceScore"] = pd.to_numeric(live.get("ConfidenceScore", 0), errors="coerce").fillna(0)
        live["WinRate"] = pd.to_numeric(live.get("WinRate", 0), errors="coerce").fillna(0)

        df = signals.merge(
            live[[
                "Ticker",
                "Pattern",
                "AlphaScore",
                "ConfidenceScore",
                "WinRate",
                "TrustLevel",
                "ValidationStatus",
            ]],
            on="Ticker",
            how="left",
        )
    else:
        df = signals.copy()
        df["Pattern"] = ""

    df["Pattern"] = df["Pattern"].fillna("").astype(str).str.strip()
    df["PatternFamily"] = df["Pattern"].apply(pattern_family)

    if not institutional.empty:
        institutional["Pattern"] = institutional["Pattern"].astype(str).str.strip()
        institutional["SurvivalScore"] = pd.to_numeric(institutional["SurvivalScore"], errors="coerce").fillna(0)
        institutional["Appearances"] = pd.to_numeric(institutional["Appearances"], errors="coerce").fillna(0)

        df = df.merge(
            institutional[[
                "Ticker",
                "Pattern",
                "InstitutionalRank",
                "Appearances",
                "SurvivalScore",
                "DiversityStatus",
            ]],
            on=["Ticker", "Pattern"],
            how="left",
        )

    if not events.empty:
        events["Pattern"] = events["Pattern"].astype(str).str.strip()
        events["Events"] = pd.to_numeric(events["Events"], errors="coerce").fillna(0)
        events["WinRate10D"] = pd.to_numeric(events["WinRate10D"], errors="coerce").fillna(0)
        events["AvgReturn10D"] = pd.to_numeric(events["AvgReturn10D"], errors="coerce").fillna(0)

        df = df.merge(
            events[[
                "Ticker",
                "Pattern",
                "Events",
                "WinRate10D",
                "AvgReturn10D",
            ]],
            on=["Ticker", "Pattern"],
            how="left",
        )

    if not families.empty:
        families["PatternFamily"] = families["PatternFamily"].astype(str).str.strip()
        families["FamilyScore"] = pd.to_numeric(families["FamilyScore"], errors="coerce").fillna(0)
        families["TotalEvents"] = pd.to_numeric(families["TotalEvents"], errors="coerce").fillna(0)

        df = df.merge(
            families[[
                "PatternFamily",
                "FamilyScore",
                "FamilyStrength",
                "TotalEvents",
                "AvgWinRate",
                "AvgReturn10D",
            ]],
            on="PatternFamily",
            how="left",
            suffixes=("", "_Family"),
        )

    if not liquidity.empty:
        liquidity["LiquidityStatus"] = liquidity["LiquidityStatus"].astype(str).str.strip().str.upper()

        df = df.merge(
            liquidity[["Ticker", "LiquidityStatus"]],
            on="Ticker",
            how="left",
        )
    else:
        df["LiquidityStatus"] = "UNKNOWN"

    numeric_cols = [
        "AlphaScore",
        "ConfidenceScore",
        "WinRate",
        "SurvivalScore",
        "Appearances",
        "Events",
        "WinRate10D",
        "AvgReturn10D",
        "FamilyScore",
        "TotalEvents",
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["ScoreComponent"] = df["FinalScore"] * 0.25
    df["LiveTrustComponent"] = df["ConfidenceScore"].clip(0, 100) * 0.15
    df["InstitutionalComponent"] = df["SurvivalScore"].clip(0, 100) * 0.20
    df["EventComponent"] = df["WinRate10D"].clip(0, 100) * 0.20
    df["FamilyComponent"] = df["FamilyScore"].clip(0, 100) * 0.15
    df["ReturnComponent"] = (df["AvgReturn10D"].clip(-5, 5) * 5) * 0.05

    df["MasterScore"] = (
        df["ScoreComponent"]
        + df["LiveTrustComponent"]
        + df["InstitutionalComponent"]
        + df["EventComponent"]
        + df["FamilyComponent"]
        + df["ReturnComponent"]
    ).round(2)

    df["Decision"] = "REJECT"

    df.loc[
        (df["MasterScore"] >= MIN_MASTER_SCORE)
        &
        (df["LiquidityStatus"] == "LIQUID"),
        "Decision"
    ] = "WATCH"

    df.loc[
        (df["MasterScore"] >= 70)
        &
        (df["LiquidityStatus"] == "LIQUID")
        &
        (df["WinRate10D"] >= 55)
        &
        (df["AvgReturn10D"] > 0),
        "Decision"
    ] = "PAPER_TRADE"

    df["RejectReason"] = ""

    df.loc[df["LiquidityStatus"] != "LIQUID", "RejectReason"] += "Not liquid; "
    df.loc[df["FinalScore"] < 45, "RejectReason"] += "Weak live score; "
    df.loc[df["SurvivalScore"] == 0, "RejectReason"] += "No institutional match; "
    df.loc[df["WinRate10D"] < 55, "RejectReason"] += "Weak event validation; "
    df.loc[df["FamilyScore"] < 50, "RejectReason"] += "Weak family score; "

    keep_cols = [
        "Ticker",
        "PrimarySignal",
        "FinalScore",
        "Pattern",
        "PatternFamily",
        "TrustLevel",
        "ConfidenceScore",
        "AlphaScore",
        "SurvivalScore",
        "Appearances",
        "Events",
        "WinRate10D",
        "AvgReturn10D",
        "FamilyScore",
        "FamilyStrength",
        "LiquidityStatus",
        "MasterScore",
        "Decision",
        "RejectReason",
    ]

    for col in keep_cols:
        if col not in df.columns:
            df[col] = ""

    out = df[keep_cols].copy()

    out = out.sort_values(
        by=["Decision", "MasterScore"],
        ascending=[True, False],
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print(out.head(30).to_string(index=False))
    print(f"\nSaved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()