from pathlib import Path
from datetime import datetime
import pandas as pd

FILES = {
    "latest": Path("data/latest_stock_signals.csv"),
    "live_patterns": Path("data/live_pattern_matches.csv"),
    "institutional": Path("data/institutional_opportunities.csv"),
    "trade_signals": Path("data/trade_signals.csv"),
    "market_state": Path("data/market_state.csv"),
    "live_monitor_state": Path("data/live_monitor_state.csv"),
}

OUTPUT_FILE = Path("data/pipeline_consistency_audit.csv")
SUMMARY_FILE = Path("data/pipeline_consistency_summary.txt")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return pd.DataFrame()


def file_time(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def normalize_ticker(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticker" in df.columns:
        df = df.copy()
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def get_latest_market_state(market_df: pd.DataFrame) -> str:
    if market_df.empty:
        return "UNKNOWN"

    possible_cols = ["MarketState", "Market State", "State"]

    for col in possible_cols:
        if col in market_df.columns:
            return str(market_df.iloc[-1][col]).strip().upper()

    return "UNKNOWN"


def main():
    print("\nPIPELINE CONSISTENCY AUDIT\n")

    latest = normalize_ticker(read_csv(FILES["latest"]))
    live_patterns = normalize_ticker(read_csv(FILES["live_patterns"]))
    institutional = normalize_ticker(read_csv(FILES["institutional"]))
    trade_signals = normalize_ticker(read_csv(FILES["trade_signals"]))
    market_state = read_csv(FILES["market_state"])
    live_monitor_state = read_csv(FILES["live_monitor_state"])

    if latest.empty:
        print("Missing latest_stock_signals.csv")
        return

    base_cols = ["Ticker", "PrimarySignal", "MarketRegime", "Volatility", "FinalScore"]

    missing = [c for c in base_cols if c not in latest.columns]
    if missing:
        print(f"latest_stock_signals.csv missing columns: {missing}")
        return

    audit = latest[base_cols].copy()

    audit = audit.rename(columns={
        "PrimarySignal": "LatestSignal",
        "MarketRegime": "LatestRegime",
        "Volatility": "LatestVolatility",
        "FinalScore": "LatestFinalScore",
    })

    if not live_patterns.empty and "Pattern" in live_patterns.columns:
        live_cols = ["Ticker", "Pattern"]
        if "PrimarySignal" in live_patterns.columns:
            live_cols.append("PrimarySignal")
        if "MarketRegime" in live_patterns.columns:
            live_cols.append("MarketRegime")
        if "TrustLevel" in live_patterns.columns:
            live_cols.append("TrustLevel")

        temp = live_patterns[live_cols].copy()

        rename_map = {
            "Pattern": "LivePattern",
            "PrimarySignal": "LivePatternSignal",
            "MarketRegime": "LivePatternRegime",
            "TrustLevel": "LiveTrustLevel",
        }

        temp = temp.rename(columns=rename_map)

        audit = audit.merge(temp, on="Ticker", how="left")

    if not institutional.empty and "Pattern" in institutional.columns:
        temp = institutional[["Ticker", "Pattern"]].copy()
        temp = temp.rename(columns={"Pattern": "InstitutionalPattern"})
        audit = audit.merge(temp, on="Ticker", how="left")

    if not trade_signals.empty:
        trade_cols = ["Ticker", "Decision"]
        if "Reason" in trade_signals.columns:
            trade_cols.append("Reason")
        if "FinalScore" in trade_signals.columns:
            trade_cols.append("FinalScore")

        temp = trade_signals[trade_cols].copy()
        temp = temp.rename(columns={
            "Decision": "TradeDecision",
            "Reason": "TradeReason",
            "FinalScore": "TradeFinalScore",
        })

        audit = audit.merge(temp, on="Ticker", how="left")

    for col in audit.columns:
        if audit[col].dtype == object:
            audit[col] = audit[col].fillna("").astype(str).str.strip()

    audit["SignalMismatch"] = False
    if "LivePatternSignal" in audit.columns:
        audit["SignalMismatch"] = (
            (audit["LivePatternSignal"] != "")
            &
            (audit["LatestSignal"] != audit["LivePatternSignal"])
        )

    audit["RegimeMismatch"] = False
    if "LivePatternRegime" in audit.columns:
        audit["RegimeMismatch"] = (
            (audit["LivePatternRegime"] != "")
            &
            (audit["LatestRegime"] != audit["LivePatternRegime"])
        )

    # Pattern comparison
        # Pattern comparison
    audit["PatternMismatch"] = False

    if (
        "LivePattern" in audit.columns
        and "InstitutionalPattern" in audit.columns
    ):

        live_clean = (
            audit["LivePattern"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        inst_clean = (
            audit["InstitutionalPattern"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        valid_live = (
            (live_clean != "")
            & (live_clean != "nan")
            & (live_clean != "none")
        )

        valid_inst = (
            (inst_clean != "")
            & (inst_clean != "nan")
            & (inst_clean != "none")
        )

        audit["PatternMismatch"] = (
            valid_live
            & valid_inst
            & (live_clean != inst_clean)
        )

    audit["AuditStatus"] = "OK"

    audit.loc[
        audit["SignalMismatch"]
        | audit["RegimeMismatch"]
        | audit["PatternMismatch"],
        "AuditStatus"
    ] = "CHECK"
    latest_market_state = get_latest_market_state(market_state)

    monitor_market_state = "UNKNOWN"
    if not live_monitor_state.empty:
        for col in ["MarketState", "Market State", "State"]:
            if col in live_monitor_state.columns:
                monitor_market_state = str(live_monitor_state.iloc[-1][col]).strip().upper()
                break

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUTPUT_FILE, index=False)

    summary_lines = [
        "PIPELINE CONSISTENCY AUDIT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "FILE TIMES",
    ]

    for name, path in FILES.items():
        summary_lines.append(f"{name}: {file_time(path)}")

    summary_lines += [
        "",
        "MARKET STATE CHECK",
        f"market_state.csv latest state: {latest_market_state}",
        f"live_monitor_state.csv state: {monitor_market_state}",
        f"Market state mismatch: {latest_market_state != monitor_market_state}",
        "",
        "TICKER CONSISTENCY",
        f"Rows checked: {len(audit)}",
        f"Signal mismatches: {int(audit['SignalMismatch'].sum())}",
        f"Regime mismatches: {int(audit['RegimeMismatch'].sum())}",
        f"Pattern mismatches: {int(audit['PatternMismatch'].sum())}",
        f"Rows needing check: {int((audit['AuditStatus'] == 'CHECK').sum())}",
        "",
        f"Saved audit -> {OUTPUT_FILE}",
    ]

    SUMMARY_FILE.write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n".join(summary_lines))

    flagged = audit[audit["AuditStatus"] == "CHECK"].copy()

    if not flagged.empty:
        print("\nFLAGGED ROWS\n")
        cols = [
            "Ticker",
            "LatestSignal",
            "LivePatternSignal",
            "LatestRegime",
            "LivePatternRegime",
            "LivePattern",
            "InstitutionalPattern",
            "SignalMismatch",
            "RegimeMismatch",
            "PatternMismatch",
        ]
        cols = [c for c in cols if c in flagged.columns]
        print(flagged[cols].head(30).to_string(index=False))


if __name__ == "__main__":
    main()