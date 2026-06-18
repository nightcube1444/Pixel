import pandas as pd
from datetime import datetime
from pathlib import Path

# File paths
input_path = Path("data/behavior_events.csv")
log_path = Path("data/live_signal_log.csv")

# Load source file
df = pd.read_csv(input_path)

# Check required columns
required_columns = ["Date", "Ticker"]
missing_required = [col for col in required_columns if col not in df.columns]
if missing_required:
    raise ValueError(f"Missing required columns in {input_path}: {missing_required}")

# Convert Date column safely
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).copy()

if df.empty:
    raise ValueError("behavior_events.csv has no valid dated rows.")

# Get latest signal date
latest_signal_date = df["Date"].max()

# Keep only latest rows
latest_df = df[df["Date"] == latest_signal_date].copy()

# Add run date
latest_df["RunDate"] = pd.Timestamp(datetime.now().date())

# Columns you want if available
columns_to_keep = [
    "RunDate",
    "Date",
    "Ticker",
    "Close",
    "BehaviorLabel",
    "SignalStrengthScore",
    "SignalStrengthLabel",
    "RareEventLabel"
]

# Keep only existing columns
available_columns = [col for col in columns_to_keep if col in latest_df.columns]
missing_optional = [col for col in columns_to_keep if col not in latest_df.columns]

if missing_optional:
    print(f"Warning: Missing optional columns skipped: {missing_optional}")

latest_df = latest_df[available_columns]

# Rename Date to SignalDate for clarity
if "Date" in latest_df.columns:
    latest_df = latest_df.rename(columns={"Date": "SignalDate"})

# If file already exists, merge and dedupe
if log_path.exists():
    existing_df = pd.read_csv(log_path)

    combined_df = pd.concat([existing_df, latest_df], ignore_index=True)

    # Only dedupe if all key columns exist
    dedupe_keys = ["RunDate", "SignalDate", "Ticker"]
    available_dedupe_keys = [col for col in dedupe_keys if col in combined_df.columns]

    if len(available_dedupe_keys) == len(dedupe_keys):
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=dedupe_keys, keep="last")
        after_count = len(combined_df)
        removed_count = before_count - after_count
        if removed_count > 0:
            print(f"Removed {removed_count} duplicate rows.")
    else:
        print(f"Warning: Could not fully dedupe because keys are missing: {dedupe_keys}")

    combined_df.to_csv(log_path, index=False)
else:
    latest_df.to_csv(log_path, index=False)

print(f"Live signals logged for {latest_signal_date.date()} in {log_path}")