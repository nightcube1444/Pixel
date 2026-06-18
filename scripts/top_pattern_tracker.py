import pandas as pd
from pathlib import Path

input_path = Path("data/research_results.csv")
output_path = Path("data/top_patterns.csv")

if not input_path.exists():
    raise FileNotFoundError(f"Missing file: {input_path}")

df = pd.read_csv(input_path)

if df.empty:
    raise ValueError("research_results.csv is empty.")

print("Columns found:", list(df.columns))

required_cols = ["Signal", "Count", "WinRate5D", "AvgReturn5D"]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

# Remove rows with zero count
df = df[df["Count"].fillna(0) > 0].copy()

if df.empty:
    raise ValueError("No valid patterns found after filtering Count > 0.")

# Sort strongest patterns first
df = df.sort_values(
    by=["AvgReturn5D", "WinRate5D", "Count"],
    ascending=[False, False, False]
).reset_index(drop=True)

df["Rank"] = df.index + 1

top_patterns = df[[
    "Rank",
    "Signal",
    "Count",
    "WinRate5D",
    "AvgReturn5D"
]].copy()

print("\nTOP PATTERN TRACKER RESULTS\n")
print(top_patterns.head(20))

top_patterns.to_csv(output_path, index=False)
print(f"\nSaved to {output_path}")