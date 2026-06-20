from pathlib import Path
from datetime import datetime
import pandas as pd

WATCHLIST_PATH = Path("data/speculative_watchlist.csv")
CROSS_ASSET_PATH = Path("data/cross_asset_pattern_recognition.csv")
OUTPUT_PATH = Path("data/trade_signals.csv")

ACCOUNT_SIZE = 10000
RISK_PER_TRADE_PCT = 1.0
STOP_LOSS_PCT = 7.0
TARGET_PCT = 15.0


def safe_read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return None


def calculate_position_size(entry_price, stop_loss):
    risk_amount = ACCOUNT_SIZE * (RISK_PER_TRADE_PCT / 100)
    risk_per_share = entry_price - stop_loss

    if risk_per_share <= 0:
        return 0

    return int(risk_amount / risk_per_share)


def build_price_plan(row):
    entry = float(row.get("Close", 0))

    if entry <= 0:
        return "", "", "", "", ""

    stop_loss = entry * (1 - STOP_LOSS_PCT / 100)
    target = entry * (1 + TARGET_PCT / 100)
    shares = calculate_position_size(entry, stop_loss)
    capital_needed = shares * entry

    return (
        round(entry, 2),
        round(target, 2),
        round(stop_loss, 2),
        shares,
        round(capital_needed, 2),
    )


def make_signal(row, decision, reason, include_price_plan=False):
    if include_price_plan:
        entry, target, stop_loss, shares, capital_needed = build_price_plan(row)
    else:
        entry, target, stop_loss, shares, capital_needed = "", "", "", "", ""

    return {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Ticker": row.get("Ticker", ""),
        "Decision": decision,
        "Reason": reason,
        "EntryPrice": entry,
        "TargetPrice": target,
        "StopLoss": stop_loss,
        "RiskPerTradePct": RISK_PER_TRADE_PCT if include_price_plan else "",
        "MaxLossAmount": round(ACCOUNT_SIZE * (RISK_PER_TRADE_PCT / 100), 2) if include_price_plan else "",
        "Shares": shares,
        "CapitalNeeded": capital_needed,
        "FinalScore": row.get("FinalScore", 0),
        "AlphaScore": row.get("AlphaScore", 0),
        "WinRate": row.get("WinRate", 0),
        "Trades": row.get("Trades", 0),
        "RiskLevel": row.get("RiskLevel", ""),
        "ActionSource": row.get("Action", ""),
        "CrossAssetActionBias": row.get("ActionBias", ""),
        "PatternType": row.get("PatternType", ""),
    }


def main():
    watchlist = safe_read_csv(WATCHLIST_PATH)
    cross_asset = safe_read_csv(CROSS_ASSET_PATH)

    if watchlist is None:
        print("Missing speculative_watchlist.csv. Run speculative_watchlist_engine.py first.")
        return

    watchlist = watchlist.copy()

    if cross_asset is not None:
        cross_asset = cross_asset.copy()

        keep_cols = [
            "Ticker",
            "ActionBias",
            "PatternType",
            "RiskMeaning",
        ]

        existing = [c for c in keep_cols if c in cross_asset.columns]

        watchlist = watchlist.merge(
            cross_asset[existing],
            on="Ticker",
            how="left"
        )

    for col in ["ActionBias", "PatternType", "RiskMeaning"]:
        if col not in watchlist.columns:
            watchlist[col] = ""

    rows = []

    for _, row in watchlist.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        signal = str(row.get("PrimarySignal", "")).strip()
        action = str(row.get("Action", "")).strip()
        action_bias = str(row.get("ActionBias", "")).strip()

        final_score = float(row.get("FinalScore", 0))
        alpha_score = float(row.get("AlphaScore", 0))
        winrate = float(row.get("WinRate", 0))
        trades = float(row.get("Trades", 0))

        if not ticker:
            continue

        # Cross-asset risk block
        if action_bias == "PAPER_ONLY_LOW_SAMPLE":
            rows.append(make_signal(
                row,
                "NO_TRADE",
                "Low sample size. Not enough evidence. Avoid for now.",
                include_price_plan=False

            ))
            continue
        
        if action_bias in ["AVOID", "WATCH_ONLY", "CAUTIOUS"]:
            rows.append(make_signal(
            row,
            "WATCH",
            f"Cross-asset risk is {action_bias}. Paper trade only.",
            include_price_plan=True
        ))
        continue

        buy_condition = (
            action in ["WATCH", "WATCH_CLOSELY"]
            and signal == "MOMENTUM"
            and final_score >= 55
            and alpha_score > 0
            and trades >= 100
        )

        strong_buy_condition = (
            buy_condition
            and winrate >= 55
            and action_bias in ["BUY_CANDIDATE_PAPER_FIRST", "WATCH"]
        )

        if strong_buy_condition:
            rows.append(make_signal(
                row,
                "BUY_CANDIDATE",
                "Strong setup, but still paper trade first before real money.",
                include_price_plan=True
            ))

        elif buy_condition:
            rows.append(make_signal(
                row,
                "WATCH",
                "Good setup, but not strong enough for real-money buy.",
                include_price_plan=True
            ))

        else:
            rows.append(make_signal(
                row,
                "NO_TRADE",
                "No clean buy setup. Avoid for now.",
                include_price_plan=False
            ))

    result = pd.DataFrame(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print("\nTRADE SIGNAL ENGINE\n")
    print(result.to_string(index=False))
    print()
    print(f"Rows: {len(result)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()