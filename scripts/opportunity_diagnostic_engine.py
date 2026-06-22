from pathlib import Path
import pandas as pd

SIGNALS_PATH = Path("data/latest_stock_signals.csv")
LIVE_PATTERNS_PATH = Path("data/live_pattern_matches.csv")
INSTITUTIONAL_PATH = Path("data/institutional_opportunities.csv")
EVENT_VALIDATION_PATH = Path("data/pattern_event_validation_results.csv")
LIQUIDITY_PATH = Path("data/liquidity_report.csv")
FINAL_CANDIDATES_PATH = Path("data/final_trade_candidates.csv")

OUTPUT_PATH = Path("data/opportunity_diagnostic_report.csv")
SUMMARY_PATH = Path("data/opportunity_diagnostic_summary.txt")

ENTRY_SIGNALS = {"PANIC", "MOMENTUM"}
MIN_SCORE = 55.0
MIN_APPEARANCES = 500
MIN_SURVIVAL = 55
MIN_EVENT_COUNT = 30
MIN_EVENT_WINRATE_10D = 55.0
MIN_EVENT_AVG_RETURN_10D = 0.0


def safe_read(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def normalize_ticker(df):
    if "Ticker" in df.columns:
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def main():
    print("\nOPPORTUNITY DIAGNOSTIC ENGINE\n")

    signals = normalize_ticker(safe_read(SIGNALS_PATH))
    live = normalize_ticker(safe_read(LIVE_PATTERNS_PATH))
    institutional = normalize_ticker(safe_read(INSTITUTIONAL_PATH))
    events = normalize_ticker(safe_read(EVENT_VALIDATION_PATH))
    liquidity = normalize_ticker(safe_read(LIQUIDITY_PATH))
    final_candidates = normalize_ticker(safe_read(FINAL_CANDIDATES_PATH))

    if signals.empty:
        print("Missing latest_stock_signals.csv")
        return

    signals["PrimarySignal"] = signals["PrimarySignal"].astype(str).str.strip().str.upper()
    signals["FinalScore"] = pd.to_numeric(signals["FinalScore"], errors="coerce").fillna(0)

    if not live.empty and "Pattern" in live.columns:
        live["Pattern"] = live["Pattern"].astype(str).str.strip()
        signals = signals.merge(
            live[["Ticker", "Pattern"]],
            on="Ticker",
            how="left",
        )
    else:
        signals["Pattern"] = ""

    signals["Pattern"] = signals["Pattern"].fillna("").astype(str).str.strip()

    step1 = signals.copy()

    step2 = step1[
        (step1["PrimarySignal"].isin(ENTRY_SIGNALS))
        &
        (step1["FinalScore"] >= MIN_SCORE)
    ].copy()

    if institutional.empty:
        institutional_pairs = set()
    else:
        institutional["Pattern"] = institutional["Pattern"].astype(str).str.strip()
        institutional["Appearances"] = pd.to_numeric(institutional["Appearances"], errors="coerce").fillna(0)
        institutional["SurvivalScore"] = pd.to_numeric(institutional["SurvivalScore"], errors="coerce").fillna(0)

        institutional = institutional[
            (institutional["Appearances"] >= MIN_APPEARANCES)
            &
            (institutional["SurvivalScore"] >= MIN_SURVIVAL)
        ].copy()

        institutional_pairs = set(zip(institutional["Ticker"], institutional["Pattern"]))

    step3 = step2[
        step2.apply(
            lambda row: (
                str(row["Ticker"]).strip().upper(),
                str(row["Pattern"]).strip(),
            ) in institutional_pairs,
            axis=1,
        )
    ].copy()

    if events.empty:
        event_pairs = set()
    else:
        events["Pattern"] = events["Pattern"].astype(str).str.strip()
        events["Events"] = pd.to_numeric(events["Events"], errors="coerce").fillna(0)
        events["AvgReturn10D"] = pd.to_numeric(events["AvgReturn10D"], errors="coerce").fillna(0)
        events["WinRate10D"] = pd.to_numeric(events["WinRate10D"], errors="coerce").fillna(0)

        events = events[
            (events["Events"] >= MIN_EVENT_COUNT)
            &
            (events["WinRate10D"] >= MIN_EVENT_WINRATE_10D)
            &
            (events["AvgReturn10D"] > MIN_EVENT_AVG_RETURN_10D)
        ].copy()

        event_pairs = set(zip(events["Ticker"], events["Pattern"]))

    step4 = step3[
        step3.apply(
            lambda row: (
                str(row["Ticker"]).strip().upper(),
                str(row["Pattern"]).strip(),
            ) in event_pairs,
            axis=1,
        )
    ].copy()

    if liquidity.empty:
        liquid_tickers = set()
    else:
        liquidity["LiquidityStatus"] = liquidity["LiquidityStatus"].astype(str).str.strip().str.upper()
        liquid_tickers = set(
            liquidity[liquidity["LiquidityStatus"] == "LIQUID"]["Ticker"]
        )

    step5 = step4[
        step4["Ticker"].isin(liquid_tickers)
    ].copy()

    if final_candidates.empty:
        final_tickers = set()
    else:
        final_tickers = set(final_candidates["Ticker"])

    step6 = step5[
        step5["Ticker"].isin(final_tickers)
    ].copy()

    summary = [
        "OPPORTUNITY DIAGNOSTIC SUMMARY",
        "--------------------------------",
        f"Total latest signals: {len(step1)}",
        f"Score-qualified signals: {len(step2)}",
        f"Institutional matched: {len(step3)}",
        f"Event validated: {len(step4)}",
        f"Liquid after validation: {len(step5)}",
        f"Final candidates survived: {len(step6)}",
        "",
        "Final surviving tickers:",
        ", ".join(step6["Ticker"].tolist()) if not step6.empty else "None",
    ]

    rows = [
        {"Step": "Total latest signals", "Count": len(step1)},
        {"Step": "Score-qualified signals", "Count": len(step2)},
        {"Step": "Institutional matched", "Count": len(step3)},
        {"Step": "Event validated", "Count": len(step4)},
        {"Step": "Liquid after validation", "Count": len(step5)},
        {"Step": "Final candidates survived", "Count": len(step6)},
    ]

    out = pd.DataFrame(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)
    SUMMARY_PATH.write_text("\n".join(summary), encoding="utf-8")

    print("\n".join(summary))
    print(f"\nSaved to {OUTPUT_PATH}")
    print(f"Saved to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()