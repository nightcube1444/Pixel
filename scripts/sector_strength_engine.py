from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
SIGNALS_PATH = BASE_DIR / "data" / "latest_stock_signals.csv"
OUTPUT_PATH = BASE_DIR / "data" / "sector_strength.csv"

# Map tickers to broad sectors. Use Yahoo Finance base tickers without exchange suffix.
SECTOR_MAP = {
    # US - Technology / Communication
    "AAPL": "TECH", "MSFT": "TECH", "NVDA": "TECH", "AMD": "TECH", "INTC": "TECH",
    "GOOGL": "TECH", "GOOG": "TECH", "META": "TECH", "NFLX": "TECH", "ADBE": "TECH",
    "CRM": "TECH", "ORCL": "TECH", "AVGO": "TECH", "QCOM": "TECH", "TSM": "TECH",

    # US - Consumer / Retail / EV
    "AMZN": "CONSUMER", "TSLA": "CONSUMER", "WMT": "CONSUMER", "COST": "CONSUMER",
    "HD": "CONSUMER", "MCD": "CONSUMER", "NKE": "CONSUMER", "SBUX": "CONSUMER",

    # US - Financial
    "JPM": "FINANCIAL", "BAC": "FINANCIAL", "GS": "FINANCIAL", "MS": "FINANCIAL",
    "V": "FINANCIAL", "MA": "FINANCIAL", "AXP": "FINANCIAL", "PYPL": "FINANCIAL",
    "BRK-B": "FINANCIAL", "BLK": "FINANCIAL",

    # US - Energy
    "XOM": "ENERGY", "CVX": "ENERGY", "COP": "ENERGY", "SLB": "ENERGY", "OXY": "ENERGY",

    # US - Healthcare
    "JNJ": "HEALTHCARE", "UNH": "HEALTHCARE", "PFE": "HEALTHCARE", "MRK": "HEALTHCARE",
    "ABBV": "HEALTHCARE", "LLY": "HEALTHCARE", "TMO": "HEALTHCARE", "ABT": "HEALTHCARE",

    # US - Industrials / Defense
    "BA": "INDUSTRIAL", "CAT": "INDUSTRIAL", "GE": "INDUSTRIAL", "HON": "INDUSTRIAL",
    "LMT": "INDUSTRIAL", "RTX": "INDUSTRIAL", "UPS": "INDUSTRIAL",

    # US - ETFs / Index proxies
    "SPY": "ETF", "QQQ": "ETF", "DIA": "ETF", "IWM": "ETF", "VTI": "ETF",
    "XLK": "TECH", "XLF": "FINANCIAL", "XLE": "ENERGY", "XLV": "HEALTHCARE",
    "XLY": "CONSUMER", "XLI": "INDUSTRIAL",

    # India - Technology
    "INFY": "TECH", "TCS": "TECH", "WIPRO": "TECH", "HCLTECH": "TECH", "TECHM": "TECH",

    # India - Financial
    "HDFCBANK": "FINANCIAL", "ICICIBANK": "FINANCIAL", "SBIN": "FINANCIAL",
    "AXISBANK": "FINANCIAL", "KOTAKBANK": "FINANCIAL", "BAJFINANCE": "FINANCIAL",

    # India - Energy / Materials
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "IOC": "ENERGY", "BPCL": "ENERGY",
    "TATASTEEL": "MATERIALS", "HINDALCO": "MATERIALS", "JSWSTEEL": "MATERIALS",

    # India - Consumer / Auto / Healthcare
    "ITC": "CONSUMER", "HINDUNILVR": "CONSUMER", "NESTLEIND": "CONSUMER", "TITAN": "CONSUMER",
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "EICHERMOT": "AUTO",
    "SUNPHARMA": "HEALTHCARE", "CIPLA": "HEALTHCARE", "DRREDDY": "HEALTHCARE",

    # Crypto
    "BTC-USD": "CRYPTO", "ETH-USD": "CRYPTO", "SOL-USD": "CRYPTO", "BNB-USD": "CRYPTO",
    
    # Commodity
    

    "SLV": "COMMODITY",

    "GDX": "COMMODITY",

    "USO": "COMMODITY",

    "DBC": "COMMODITY",
    "BEL": "DEFENSE",
    "BHARTIARTL": "COMMUNICATION",
    "BSE": "FINANCIAL",
    "CDSL": "FINANCIAL",
    "COCHINSHIP": "DEFENSE",
    "HAL": "DEFENSE",
    "IDEA": "COMMUNICATION",
    "IREDA": "FINANCIAL",
    "IRFC": "FINANCIAL",
    "KPITTECH": "TECH",
    "LT": "INDUSTRIAL",
    "NMDC": "METALS",
    "NOC": "DEFENSE",
    "PERSISTENT": "TECH",
    "RKLB": "SPACE",
    "RVNL": "INDUSTRIAL",
    "SAIL": "METALS",
    "SUZLON": "ENERGY",
    "YESBANK": "FINANCIAL",
    "^VIX": "VOLATILITY",
    "GLD": "COMMODITY",
    "IRDM": "SPACE",

    
}


def normalize_ticker(ticker: str) -> str:
    """Convert Yahoo tickers like RELIANCE.NS into RELIANCE for sector lookup."""
    ticker = str(ticker).strip().upper()
    if ticker.endswith(".NS") or ticker.endswith(".BO") or ticker.endswith(".TO"):
        return ticker.split(".")[0]
    return ticker


def main() -> None:
    if not SIGNALS_PATH.exists():
        print(f"Missing file: {SIGNALS_PATH}")
        print("Run this first: python3 scripts/signal_engine.py")
        raise SystemExit(1)

    df = pd.read_csv(SIGNALS_PATH)

    required_cols = ["Ticker", "FinalScore"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Missing columns in latest_stock_signals.csv: {missing_cols}")
        raise SystemExit(1)

    df["FinalScore"] = pd.to_numeric(df["FinalScore"], errors="coerce")
    df = df.dropna(subset=["Ticker", "FinalScore"]).copy()

    df["TickerKey"] = df["Ticker"].apply(normalize_ticker)
    df["Sector"] = df["TickerKey"].map(SECTOR_MAP)

    unmapped = sorted(df.loc[df["Sector"].isna(), "Ticker"].dropna().unique().tolist())
    df = df.dropna(subset=["Sector"])

    if df.empty:
        print("No sector mappings found.")
        if unmapped:
            print("Unmapped tickers:", unmapped[:50])
        raise SystemExit(1)

    sector_df = (
        df.groupby("Sector")
        .agg(
            AvgScore=("FinalScore", "mean"),
            MaxScore=("FinalScore", "max"),
            MinScore=("FinalScore", "min"),
            StockCount=("Ticker", "count"),
            TopTicker=("Ticker", lambda x: df.loc[x.index].sort_values("FinalScore", ascending=False).iloc[0]["Ticker"]),
        )
        .reset_index()
    )

    for col in ["AvgScore", "MaxScore", "MinScore"]:
        sector_df[col] = sector_df[col].round(2)

    sector_df = sector_df.sort_values("AvgScore", ascending=False).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sector_df.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(" MINI CUBE SECTOR STRENGTH")
    print("===================================\n")
    print(sector_df.to_string(index=False))

    leader = sector_df.iloc[0]
    print("\nStrongest Sector")
    print("-------------------")
    print(f"{leader['Sector']} (Avg Score {leader['AvgScore']}) | Top ticker: {leader['TopTicker']}")

    if unmapped:
        print("\nUnmapped tickers skipped")
        print("-------------------")
        print(", ".join(unmapped[:50]))
        if len(unmapped) > 50:
            print(f"...and {len(unmapped) - 50} more")

    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
