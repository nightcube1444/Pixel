import pandas as pd
from pathlib import Path
from datetime import datetime

# Load latest discovery results
discovery_path = "data/signal_discovery_results.csv"

if not Path(discovery_path).exists():
    print("signal_discovery_results.csv not found.")
    exit()

df = pd.read_csv(discovery_path)

if df.empty:
    print("No discovery results to store.")
    exit()

# Add snapshot date
today = datetime.today().strftime("%Y-%m-%d")
df["SnapshotDate"] = today

# Reorder columns
cols = ["SnapshotDate"] + [col for col in df.columns if col != "SnapshotDate"]
df = df[cols]

memory_path = Path("data/market_memory.csv")

# Append to existing memory file
if memory_path.exists():
    old_df = pd.read_csv(memory_path)
    combined_df = pd.concat([old_df, df], ignore_index=True)
    combined_df.to_csv(memory_path, index=False)
else:
    df.to_csv(memory_path, index=False)

print("Market memory updated and saved to data/market_memory.csv")
print(df.head())