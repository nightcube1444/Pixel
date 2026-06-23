from pathlib import Path
import pandas as pd

LIVE_MATCHES_FILE = Path(
    "data/cross_asset_pattern_recognition.csv"
)

TRUST_FILE = Path(
    "data/trusted_patterns.csv"
)

OUTPUT_FILE = Path(
    "data/live_pattern_matches.csv"
)


def safe_read(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        print(f"Missing or empty file: {path}")
        return pd.DataFrame()

    return pd.read_csv(path)


def main():
    print("\nLIVE PATTERN MATCH ENGINE\n")

    live_matches = safe_read(LIVE_MATCHES_FILE)
    trust_df = safe_read(TRUST_FILE)

    if live_matches.empty:
        return

    if trust_df.empty:
        return

    if "Pattern" not in live_matches.columns:
        if "CrossAssetPattern" in live_matches.columns:
            live_matches["Pattern"] = live_matches["CrossAssetPattern"]
        else:
            print("Missing Pattern or CrossAssetPattern column.")
            return

    required_live = [
        "Ticker",
        "Pattern",
    ]

    missing_live = [
        c for c in required_live
        if c not in live_matches.columns
    ]

    if missing_live:
        print(f"Live matches missing columns: {missing_live}")
        return

    required_trust = [
        "Pattern",
        "TrustLevel",
        "ConfidenceScore",
        "PValue",
        "ValidationStatus",
    ]

    missing_trust = [
        c for c in required_trust
        if c not in trust_df.columns
    ]

    if missing_trust:
        print(f"Trusted patterns missing columns: {missing_trust}")
        return

    live_matches = live_matches.copy()
    trust_df = trust_df.copy()

    live_matches["Ticker"] = (
        live_matches["Ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    live_matches["Pattern"] = (
        live_matches["Pattern"]
        .astype(str)
        .str.strip()
    )

    trust_df["Pattern"] = (
        trust_df["Pattern"]
        .astype(str)
        .str.strip()
    )

    trust_df = trust_df[
        [
            "Pattern",
            "TrustLevel",
            "ConfidenceScore",
            "PValue",
            "ValidationStatus",
        ]
    ].drop_duplicates(
        subset=["Pattern"],
        keep="first",
    )

    columns_to_remove = [
        "TrustLevel",
        "ConfidenceScore",
        "PValue",
        "ValidationStatus",
        "TrustRank",
    ]

    live_matches = live_matches.drop(
        columns=[
            col
            for col in columns_to_remove
            if col in live_matches.columns
        ],
        errors="ignore",
    )

    live_matches = live_matches.merge(
        trust_df,
        on="Pattern",
        how="left",
        validate="many_to_one",
    )

    live_matches["TrustLevel"] = (
        live_matches["TrustLevel"]
        .fillna("UNTRUSTED")
    )

    live_matches["ConfidenceScore"] = (
        pd.to_numeric(
            live_matches["ConfidenceScore"],
            errors="coerce",
        )
        .fillna(0)
    )

    live_matches["PValue"] = (
        pd.to_numeric(
            live_matches["PValue"],
            errors="coerce",
        )
        .fillna(1)
    )

    live_matches["ValidationStatus"] = (
        live_matches["ValidationStatus"]
        .fillna("NOT_VALIDATED")
    )

    trust_rank_map = {
        "INSTITUTIONAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "UNTRUSTED": 1,
    }

    live_matches["TrustRank"] = (
        live_matches["TrustLevel"]
        .map(trust_rank_map)
        .fillna(1)
        .astype(int)
    )

    if "AlphaScore" not in live_matches.columns:
        live_matches["AlphaScore"] = 0

    if "WinRate" not in live_matches.columns:
        live_matches["WinRate"] = 0

    live_matches["AlphaScore"] = pd.to_numeric(
        live_matches["AlphaScore"],
        errors="coerce",
    ).fillna(0)

    live_matches["WinRate"] = pd.to_numeric(
        live_matches["WinRate"],
        errors="coerce",
    ).fillna(0)

    live_matches = live_matches.sort_values(
        by=[
            "TrustRank",
            "AlphaScore",
            "ConfidenceScore",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    live_matches.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    display_cols = [
        "Ticker",
        "Pattern",
        "TrustLevel",
        "ConfidenceScore",
        "WinRate",
        "AlphaScore",
    ]

    print(
        live_matches[display_cols]
        .head(25)
        .to_string(index=False)
    )

    print("\nTrust Summary")
    print(
        live_matches["TrustLevel"]
        .value_counts()
    )

    print(f"\nMatches found: {len(live_matches)}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()