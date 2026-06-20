from pathlib import Path
from datetime import datetime
import pandas as pd

LATEST_SIGNALS_PATH = Path("data/latest_stock_signals.csv")
BENCHMARK_CONTEXT_PATH = Path("data/benchmark_context.csv")
ALPHA_PATH = Path("data/alpha_ranking_results.csv")

OUTPUT_PATH = Path("data/cross_asset_pattern_recognition.csv")
SUMMARY_PATH = Path("data/cross_asset_pattern_summary.txt")


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


def clean_value(value, default="UNKNOWN"):
    text = str(value).strip().upper()

    if text in ["", "NAN", "NONE"]:
        return default

    return text


def classify_pattern_type(primary_signal, stock_regime, volatility, spy_regime, vix_state):
    if spy_regime == "BULL" and vix_state in ["VIX_LOW"]:
        return "HEALTHY_RISK_ON"

    if spy_regime == "BULL" and vix_state in ["VIX_ELEVATED"]:
        return "TENSE_BULL"

    if spy_regime == "BULL" and vix_state in ["VIX_HIGH", "VIX_EXTREME"]:
        return "RISKY_BULL"

    if spy_regime == "BEAR" and vix_state in ["VIX_HIGH", "VIX_EXTREME"]:
        return "DANGER_ZONE"

    if spy_regime == "SIDEWAYS" and vix_state in ["VIX_ELEVATED", "VIX_HIGH"]:
        return "CHOPPY_MARKET"

    if stock_regime == "HIGH_VOLATILITY" and volatility == "VOLATILE":
        return "HIGH_VOL_STOCK_SETUP"

    if primary_signal == "PANIC":
        return "PANIC_SETUP"

    if primary_signal == "MOMENTUM":
        return "MOMENTUM_SETUP"

    return "NORMAL_CONTEXT"


def explain_risk(pattern_type, primary_signal, stock_regime, vix_state):
    if pattern_type == "HEALTHY_RISK_ON":
        return "Market background is supportive. Momentum signals are cleaner, but still need confirmation."

    if pattern_type == "TENSE_BULL":
        return "SPY is bullish, but VIX is elevated. Signals can work, but risk is higher than normal."

    if pattern_type == "RISKY_BULL":
        return "SPY is still bullish, but VIX is high. This can become unstable quickly."

    if pattern_type == "DANGER_ZONE":
        return "Bear market with high volatility. Speculative trades are dangerous."

    if pattern_type == "CHOPPY_MARKET":
        return "Sideways market with elevated volatility. False signals are common."

    if pattern_type == "HIGH_VOL_STOCK_SETUP":
        return "The stock itself is highly volatile. Use smaller paper position size."

    if pattern_type == "PANIC_SETUP":
        return "Panic signal detected. This may be a bounce setup, but catching falling stocks is risky."

    if pattern_type == "MOMENTUM_SETUP":
        return "Momentum signal detected. Watch if strength continues."

    return "Normal context. No strong cross-asset message."


def decide_action_bias(pattern_type, primary_signal, alpha_score, winrate, trades):
    if trades < 30:
        return "PAPER_ONLY_LOW_SAMPLE"

    if pattern_type == "DANGER_ZONE":
        return "AVOID"

    if pattern_type == "RISKY_BULL":
        return "WATCH_ONLY"

    if pattern_type == "TENSE_BULL":
        if primary_signal == "MOMENTUM" and alpha_score > 0 and winrate >= 50 and trades >= 100:
            return "WATCH"
        return "CAUTIOUS"

    if pattern_type == "HEALTHY_RISK_ON":
        if primary_signal == "MOMENTUM" and alpha_score > 0 and winrate >= 55 and trades >= 100:
            return "BUY_CANDIDATE_PAPER_FIRST"
        return "WATCH"

    if primary_signal == "PANIC":
        return "PAPER_ONLY"

    if primary_signal == "MOMENTUM" and alpha_score > 0:
        return "WATCH"

    return "NO_EDGE"


def main():
    signals = safe_read_csv(LATEST_SIGNALS_PATH)
    context = safe_read_csv(BENCHMARK_CONTEXT_PATH)
    alpha = safe_read_csv(ALPHA_PATH)

    if signals is None:
        print("Missing latest_stock_signals.csv")
        return

    if context is None:
        print("Missing benchmark_context.csv")
        return

    latest_context = context.copy()
    latest_context["Date"] = pd.to_datetime(latest_context["Date"], errors="coerce")
    latest_context = latest_context.dropna(subset=["Date"])

    if latest_context.empty:
        print("No valid context dates found.")
        return

    ctx = latest_context.sort_values("Date").iloc[-1]

    spy_regime = clean_value(ctx.get("SPY_Regime", "UNKNOWN"))
    vix_state = clean_value(ctx.get("VIX_State", "UNKNOWN"))

    rows = []

    for _, row in signals.iterrows():
        ticker = str(row.get("Ticker", "")).strip()

        primary_signal = clean_value(row.get("PrimarySignal", "NONE"), default="NONE")
        stock_regime = clean_value(row.get("MarketRegime", "UNKNOWN"))
        volatility = clean_value(row.get("Volatility", "NORMAL"), default="NORMAL")

        cross_asset_pattern = (
            f"{primary_signal}|{stock_regime}|{volatility}|{spy_regime}|{vix_state}"
        )

        alpha_score = 0.0
        winrate = 0.0
        trades = 0.0
        alpha_rank = ""

        if alpha is not None and "Pattern" in alpha.columns:
            match = alpha[
                alpha["Pattern"].astype(str).str.strip() == cross_asset_pattern
            ]

            if not match.empty:
                a = match.iloc[0]
                alpha_score = float(pd.to_numeric(a.get("AlphaScore", 0), errors="coerce") or 0)
                winrate = float(pd.to_numeric(a.get("WinRate", 0), errors="coerce") or 0)
                trades = float(pd.to_numeric(a.get("Trades", 0), errors="coerce") or 0)
                alpha_rank = a.get("AlphaRank", "")

        pattern_type = classify_pattern_type(
            primary_signal,
            stock_regime,
            volatility,
            spy_regime,
            vix_state,
        )

        risk_meaning = explain_risk(
            pattern_type,
            primary_signal,
            stock_regime,
            vix_state,
        )

        action_bias = decide_action_bias(
            pattern_type,
            primary_signal,
            alpha_score,
            winrate,
            trades,
        )

        rows.append({
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Ticker": ticker,
            "Close": row.get("Close", ""),
            "PrimarySignal": primary_signal,
            "MarketRegime": stock_regime,
            "Volatility": volatility,
            "SPY_Regime": spy_regime,
            "VIX_State": vix_state,
            "CrossAssetPattern": cross_asset_pattern,
            "PatternType": pattern_type,
            "AlphaRank": alpha_rank,
            "AlphaScore": round(alpha_score, 4),
            "WinRate": round(winrate, 2),
            "Trades": trades,
            "RiskMeaning": risk_meaning,
            "ActionBias": action_bias,
        })

    result = pd.DataFrame(rows)

    result = result.sort_values(
        by=["ActionBias", "AlphaScore", "WinRate"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    important = result[
        result["ActionBias"].isin([
            "BUY_CANDIDATE_PAPER_FIRST",
            "WATCH",
            "WATCH_ONLY",
            "PAPER_ONLY",
        ])
    ].head(15)

    lines = [
        "CROSS-ASSET PATTERN RECOGNITION SUMMARY",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"SPY Regime: {spy_regime}",
        f"VIX State: {vix_state}",
        "",
        "Top actionable contexts:",
    ]

    if important.empty:
        lines.append("No actionable cross-asset patterns found.")
    else:
        for _, row in important.iterrows():
            lines.append(
                f"- {row['Ticker']} | {row['PrimarySignal']} | {row['PatternType']} | "
                f"Alpha={row['AlphaScore']} | WinRate={row['WinRate']} | "
                f"Trades={row['Trades']} | {row['ActionBias']}"
            )

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("\nCROSS-ASSET PATTERN RECOGNITION\n")
    print(result.head(25).to_string(index=False))
    print()
    print(f"Rows: {len(result)}")
    print(f"Saved to {OUTPUT_PATH}")
    print(f"Saved summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()