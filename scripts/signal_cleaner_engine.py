from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

FILES = [
    DATA_DIR / "latest_stock_signals.csv",
    DATA_DIR / "all_stock_signals.csv",
]

FILL_NO_COLUMNS = [
    "Panic",
    "Momentum",
    "Volatility",
    "RSI_Oversold",
    "RSI_Overbought",
]

OUTPUT_SUFFIX = "_cleaned"


def clean_signal_file(path: Path):
    if not path.exists():
        print(f"Missing file: {path}")
        return

    df = pd.read_csv(path)

    for col in FILL_NO_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna("NO")

    if "PatternKey" in df.columns:
        base_cols = []
        
    if "CrossAssetPattern" in df.columns:
        df["CrossAssetPattern"] = (

            df["CrossAssetPattern"]
            .astype(str)
            .str.strip()
        )

        for col in ["PrimarySignal", "MarketRegime", "Volatility"]:
            if col in df.columns:
                base_cols.append(col)

        if base_cols:
            df["PatternKey"] = (
                df[base_cols]
                .fillna("UNKNOWN")
                .astype(str)
                .agg("|".join, axis=1)
            )

    output_path = path.with_name(path.stem + OUTPUT_SUFFIX + path.suffix)
    df.to_csv(output_path, index=False)

    print(f"Cleaned: {path.name}")
    print(f"Saved to: {output_path}")


def main():
    print("\n===================================")
    print(" MINI CUBE SIGNAL CLEANER")
    print("===================================\n")

    for path in FILES:
        clean_signal_file(path)


if __name__ == "__main__":
    main()