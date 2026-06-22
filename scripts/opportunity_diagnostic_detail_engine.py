from pathlib import Path
import pandas as pd

SIGNALS_PATH = Path("data/latest_stock_signals.csv")
LIVE_PATTERNS_PATH = Path("data/live_pattern_matches.csv")
EVENT_PATH = Path("data/pattern_event_validation_results.csv")
INSTITUTIONAL_PATH = Path("data/institutional_opportunities.csv")
OUTPUT_PATH = Path("data/opportunity_diagnostic_details.csv")

ENTRY_SIGNALS = {"PANIC", "MOMENTUM"}
MIN_SCORE = 55.0
MIN_EVENTS = 30
MIN_WINRATE_10D = 55.0
MIN_AVG_RETURN_10D = 0.0


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return pd.DataFrame()

    return df


def normalize_ticker(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty and "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def build_event_lookup(event_df: pd.DataFrame) -> dict:
    lookup = {}

    if event_df.empty:
        return lookup

    event_df = normalize_ticker(event_df)
    event_df["Pattern"] = event_df["Pattern"].astype(str).str.strip()
    event_df["Events"] = pd.to_numeric(event_df["Events"], errors="coerce").fillna(0)
    event_df["WinRate10D"] = pd.to_numeric(event_df["WinRate10D"], errors="coerce").fillna(0)
    event_df["AvgReturn10D"] = pd.to_numeric(event_df["AvgReturn10D"], errors="coerce").fillna(0)

    for _, row in event_df.iterrows():
        key = (
            str(row["Ticker"]).strip().upper(),
            str(row["Pattern"]).strip(),
        )

        lookup[key] = {
            "Events": row["Events"],
            "WinRate10D": row["WinRate10D"],
            "AvgReturn10D": row["AvgReturn10D"],
        }

    return lookup


def main():
    print("\nOPPORTUNITY DIAGNOSTIC DETAIL ENGINE\n")

    signals_df = normalize_ticker(safe_read_csv(SIGNALS_PATH))
    live_df = normalize_ticker(safe_read_csv(LIVE_PATTERNS_PATH))
    institutional_df = normalize_ticker(safe_read_csv(INSTITUTIONAL_PATH))
    event_df = normalize_ticker(safe_read_csv(EVENT_PATH))

    if signals_df.empty:
        print("Missing latest_stock_signals.csv")
        return

    signals_df["PrimarySignal"] = signals_df["PrimarySignal"].astype(str).str.strip().str.upper()
    signals_df["FinalScore"] = pd.to_numeric(signals_df["FinalScore"], errors="coerce").fillna(0)

    if not live_df.empty and "Pattern" in live_df.columns:
        live_df["Pattern"] = live_df["Pattern"].astype(str).str.strip()
        merged = signals_df.merge(
            live_df[["Ticker", "Pattern"]],
            on="Ticker",
            how="left",
        )
    else:
        merged = signals_df.copy()
        merged["Pattern"] = ""

    merged["Pattern"] = merged["Pattern"].fillna("").astype(str).str.strip()

    institutional_pairs = set()

    if not institutional_df.empty:
        institutional_df["Pattern"] = institutional_df["Pattern"].astype(str).str.strip()

        institutional_pairs = set(
            zip(
                institutional_df["Ticker"],
                institutional_df["Pattern"],
            )
        )

    event_lookup = build_event_lookup(event_df)

    rows = []

    for _, row in merged.iterrows():
        ticker = str(row["Ticker"]).strip().upper()
        pattern = str(row["Pattern"]).strip()
        primary_signal = str(row["PrimarySignal"]).strip().upper()
        final_score = float(row["FinalScore"])

        score_pass = (
            primary_signal in ENTRY_SIGNALS
            and
            final_score >= MIN_SCORE
        )

        institutional_pass = (
            ticker,
            pattern,
        ) in institutional_pairs

        event_data = event_lookup.get(
            (
                ticker,
                pattern,
            ),
            None,
        )

        if event_data is None:
            events = 0
            winrate_10d = 0
            avg_return_10d = 0
        else:
            events = event_data["Events"]
            winrate_10d = event_data["WinRate10D"]
            avg_return_10d = event_data["AvgReturn10D"]

        event_pass = (
            events >= MIN_EVENTS
            and
            winrate_10d >= MIN_WINRATE_10D
            and
            avg_return_10d > MIN_AVG_RETURN_10D
        )

        fail_reasons = []

        if not score_pass:
            fail_reasons.append("Score/Signal failed")

        if score_pass and not institutional_pass:
            fail_reasons.append("No institutional match")

        if score_pass and institutional_pass and not event_pass:
            if events < MIN_EVENTS:
                fail_reasons.append(f"Events too low: {events} < {MIN_EVENTS}")
            if winrate_10d < MIN_WINRATE_10D:
                fail_reasons.append(f"WinRate10D too low: {winrate_10d} < {MIN_WINRATE_10D}")
            if avg_return_10d <= MIN_AVG_RETURN_10D:
                fail_reasons.append(f"AvgReturn10D too low: {avg_return_10d} <= {MIN_AVG_RETURN_10D}")

        if score_pass and institutional_pass and event_pass:
            final_stage = "PASSED_EVENT_VALIDATION"
        elif score_pass and institutional_pass:
            final_stage = "FAILED_EVENT_VALIDATION"
        elif score_pass:
            final_stage = "FAILED_INSTITUTIONAL"
        else:
            final_stage = "FAILED_SCORE"

        rows.append(
            {
                "Ticker": ticker,
                "PrimarySignal": primary_signal,
                "FinalScore": final_score,
                "Pattern": pattern,
                "ScorePass": score_pass,
                "InstitutionalPass": institutional_pass,
                "Events": events,
                "WinRate10D": winrate_10d,
                "AvgReturn10D": avg_return_10d,
                "EventPass": event_pass,
                "FinalStage": final_stage,
                "FailReasons": "; ".join(fail_reasons) if fail_reasons else "PASS",
            }
        )

    out_df = pd.DataFrame(rows)

    out_df = out_df.sort_values(
        by=[
            "ScorePass",
            "InstitutionalPass",
            "EventPass",
            "FinalScore",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_PATH, index=False)

    print(out_df.head(40).to_string(index=False))
    print(f"\nSaved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()