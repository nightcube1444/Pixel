from pathlib import Path
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title="Pixel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_csv(filename):
    path = DATA_DIR / filename

    if not path.exists() or path.stat().st_size == 0:
        return []

    try:
        df = pd.read_csv(path)
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        return [{"error": str(e)}]


@app.get("/")
def home():
    return {"message": "Pixel API is running"}


@app.get("/watchlist")
def watchlist():
    return read_csv("speculative_watchlist.csv")


@app.get("/trade-signals")
def trade_signals():
    return read_csv("trade_signals.csv")


@app.get("/cross-asset-patterns")
def cross_asset_patterns():
    return read_csv("cross_asset_pattern_recognition.csv")


@app.get("/latest-signals")
def latest_signals():
    return read_csv("latest_stock_signals.csv")


@app.get("/market-state")
def market_state():
    rows = read_csv("market_state.csv")
    if not rows:
        return {}
    return rows[-1]


@app.get("/candles/{ticker}")
def candles(ticker: str):
    rows = read_csv("market_data.csv")

    if not rows:
        return []

    ticker = ticker.upper().replace(".NS", "")

    result = []

    for row in rows:
        row_ticker = str(row.get("Ticker", "")).upper().replace(".NS", "")

        if row_ticker != ticker:
            continue

        try:
            result.append({
                "time": str(row.get("Date"))[:10],
                "open": float(row.get("Open")),
                "high": float(row.get("High")),
                "low": float(row.get("Low")),
                "close": float(row.get("Close")),
            })
        except Exception:
            continue

    return result[-120:]

@app.get("/explain/{ticker}")
def explain_ticker(ticker: str):
    rows = read_csv("candle_explanations.csv")

    if not rows:
        return {}

    ticker = ticker.upper().replace(".NS", "")

    for row in rows:
        row_ticker = str(row.get("Ticker", "")).upper().replace(".NS", "")

        if row_ticker == ticker:
            return row

    return {}

@app.get("/system-status")
def system_status():
    return {
        "api_status": "running",
        "backend_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
@app.get("/file-status")
def file_status():
    files = [
        "market_data.csv",
        "live_pattern_matches.csv",
        "speculative_watchlist.csv",
        "trade_signals.csv",
        "institutional_recommendations.csv",
        "research_report.txt",
    ]

    results = []

    for filename in files:
        path = DATA_DIR / filename

        if path.exists():
            modified_time = datetime.fromtimestamp(
                path.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S")

            results.append({
                "file": filename,
                "exists": True,
                "modified_time": modified_time,
                "size_kb": round(path.stat().st_size / 1024, 2),
            })
        else:
            results.append({
                "file": filename,
                "exists": False,
                "modified_time": "",
                "size_kb": 0,
            })

    return results
# ============================================================
# PATTERN EXPLANATION ENGINE
# ============================================================

def explain_pattern(pattern):
    meanings = {
        "PANIC": "Fear selling is detected. Traders may be dumping positions quickly.",
        "MOMENTUM": "Price is moving strongly in one direction with trend strength.",
        "OVERBOUGHT": "Price may be stretched upward and could be due for cooling.",
        "OVERSOLD": "Price may be stretched downward and could be due for rebound.",
        "NONE": "No strong primary signal was detected.",

        "BULL": "Bullish market regime. Price is generally trending upward.",
        "BEAR": "Bearish market regime. Price is generally trending downward.",
        "SIDEWAYS": "Range-bound market. Price is moving without a strong trend.",
        "HIGH_VOLATILITY": "Large price swings are happening. Risk is elevated.",

        "NORMAL": "Normal volatility condition.",
        "VOLATILE": "Volatility is above normal. Price movement is unstable.",
        "HIGH_VOL": "High trading volume or high activity condition.",

        "VIX_LOW": "Market fear is low.",
        "VIX_ELEVATED": "Market fear is elevated but not extreme.",
        "VIX_HIGH": "Market fear is high.",
        "VIX_EXTREME": "Market fear is extreme."
    }

    explanation = []

    for part in str(pattern).split("|"):
        clean = part.strip().upper()

        explanation.append({
            "component": clean,
            "meaning": meanings.get(
                clean,
                "No explanation available for this component."
            )
        })

    return explanation

@app.get("/system-health")
def system_health():
    watchlist = read_csv("speculative_watchlist.csv")
    live_patterns = read_csv("live_pattern_matches.csv")
    trade_signals = read_csv("trade_signals.csv")
    market_state_rows = read_csv("market_state.csv")

    files = [
        "market_data.csv",
        "live_pattern_matches.csv",
        "speculative_watchlist.csv",
        "trade_signals.csv",
        "institutional_recommendations.csv",
        "research_report.txt",
    ]

    healthy_files = 0

    for filename in files:
        path = DATA_DIR / filename
        if path.exists() and path.stat().st_size > 0:
            healthy_files += 1

    latest_market_state = {}

    if isinstance(market_state_rows, list) and len(market_state_rows) > 0:
        latest_market_state = market_state_rows[-1]

    return {
        "api_status": "ONLINE",
        "pipeline_status": "ONLINE" if healthy_files == len(files) else "WARNING",
        "backend_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist_count": len(watchlist) if isinstance(watchlist, list) else 0,
        "pattern_matches": len(live_patterns) if isinstance(live_patterns, list) else 0,
        "trade_signals": len(trade_signals) if isinstance(trade_signals, list) else 0,
        "healthy_files": healthy_files,
        "total_files": len(files),
        "market_state": latest_market_state.get("MarketState", "UNKNOWN"),
        "spy_regime": latest_market_state.get("SPY_Regime", "UNKNOWN"),
        "vix_state": latest_market_state.get("VIX_State", "UNKNOWN"),
    }
# ============================================================
# LIVE TICKER INTELLIGENCE
# ============================================================

@app.get("/live-ticker/{ticker}")
def live_ticker(ticker: str):

    ticker = ticker.upper().replace(".NS", "").strip()

    watchlist = read_csv("speculative_watchlist.csv")
    live_patterns = read_csv("live_pattern_matches.csv")

    current = None
    pattern_match = None

    for row in watchlist:
        row_ticker = str(
            row.get("Ticker", "")
        ).upper().replace(".NS", "")

        if row_ticker == ticker:
            current = row
            break

    for row in live_patterns:
        row_ticker = str(
            row.get("Ticker", "")
        ).upper().replace(".NS", "")

        if row_ticker == ticker:
            pattern_match = row
            break

    if not current and not pattern_match:
        return {
            "ticker": ticker,
            "found": False,
            "message": "No live ticker data found"
        }

    pattern = ""

    if pattern_match:
        pattern = pattern_match.get("Pattern", "")

    elif current:
        pattern = current.get("Pattern", "")

    return {
        "ticker": ticker,
        "found": True,
        "current": current,
        "pattern_match": pattern_match,
        "pattern": pattern,
        "explanation": explain_pattern(pattern) if pattern else []
    }

