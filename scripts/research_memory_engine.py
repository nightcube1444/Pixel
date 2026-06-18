import pandas as pd
from pathlib import Path
from datetime import datetime


# -----------------------------
# File paths
# -----------------------------
confidence_path = Path("data/confidence_score_results.csv")
stability_path = Path("data/pattern_stability_results.csv")
decay_path = Path("data/pattern_decay_results.csv")
signal_stats_path = Path("data/signal_statistics.csv")
memory_path = Path("data/research_memory.csv")


# -----------------------------
# Helpers
# -----------------------------
def load_csv(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            print(f"Missing required file: {path}")
            raise SystemExit(1)
        return pd.DataFrame()

    if path.stat().st_size == 0:
        if required:
            print(f"Required file is empty: {path}")
            raise SystemExit(1)
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as e:
        if required:
            print(f"Failed to read {path}: {e}")
            raise SystemExit(1)
        return pd.DataFrame()


def find_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def safe_str(value) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    return str(value).strip()


def build_pattern_from_row(row: pd.Series) -> str:
    """
    Build a standard pattern string from available columns.
    Prefers SignalSetup if it already exists.
    Otherwise combines old-style label columns.
    """
    if "SignalSetup" in row.index and pd.notna(row["SignalSetup"]):
        return str(row["SignalSetup"]).strip()

    parts = []
    for col in ["BehaviorLabel", "SignalStrengthLabel", "VolatilityLabel"]:
        if col in row.index:
            parts.append(safe_str(row[col]))
        else:
            parts.append("UNKNOWN")

    return " | ".join(parts)


def round_or_none(value, digits: int = 4):
    try:
        if pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return None


# -----------------------------
# Load source files
# -----------------------------
confidence_df = load_csv(confidence_path, required=True)
stability_df = load_csv(stability_path, required=False)
decay_df = load_csv(decay_path, required=False)
signal_stats_df = load_csv(signal_stats_path, required=False)

if confidence_df.empty:
    print("No confidence data found.")
    raise SystemExit(1)


# -----------------------------
# Normalize confidence data
# -----------------------------
# Ensure there is a Pattern column
confidence_df = confidence_df.copy()
confidence_df["Pattern"] = confidence_df.apply(build_pattern_from_row, axis=1)

# Confidence score column
confidence_score_col = find_first_existing_column(
    confidence_df,
    ["ConfidenceScore", "Score", "Confidence"]
)

# Evidence / appearances / trades
evidence_col = find_first_existing_column(
    confidence_df,
    ["Appearances", "Trades", "EvidenceCount"]
)

# Win rate / avg return
winrate_col = find_first_existing_column(
    confidence_df,
    ["AvgWinRate", "WinRate", "AverageWinRate"]
)

avgreturn_col = find_first_existing_column(
    confidence_df,
    ["AvgReturn", "AverageReturn"]
)

# First seen / last seen if present
last_seen_col = find_first_existing_column(
    confidence_df,
    ["LastSeen", "LastSeenDate", "LastDate"]
)

best_rank_col = find_first_existing_column(
    confidence_df,
    ["BestRank"]
)

worst_rank_col = find_first_existing_column(
    confidence_df,
    ["WorstRank"]
)

confidence_rank_col = find_first_existing_column(
    confidence_df,
    ["ConfidenceRank", "Rank"]
)


# -----------------------------
# Normalize stability data
# -----------------------------
stability_lookup = {}

if not stability_df.empty:
    stability_df = stability_df.copy()
    stability_df["Pattern"] = stability_df.apply(build_pattern_from_row, axis=1)

    stability_rank_col = find_first_existing_column(
        stability_df,
        ["StabilityRank", "Rank"]
    )

    for _, row in stability_df.iterrows():
        pattern = row["Pattern"]
        stability_lookup[pattern] = {
            "StabilityStatus": "STABLE" if "StabilityRank" in stability_df.columns else "UNKNOWN",
            "StabilityRank": row[stability_rank_col] if stability_rank_col else None
        }


# -----------------------------
# Normalize decay data
# -----------------------------
decay_lookup = {}

if not decay_df.empty:
    decay_df = decay_df.copy()
    decay_df["Pattern"] = decay_df.apply(build_pattern_from_row, axis=1)

    decay_label_col = find_first_existing_column(
        decay_df,
        ["DecayLabel", "Status", "DecayStatus"]
    )

    for _, row in decay_df.iterrows():
        pattern = row["Pattern"]
        decay_lookup[pattern] = {
            "DecayStatus": safe_str(row[decay_label_col]) if decay_label_col else "UNKNOWN"
        }


# -----------------------------
# Normalize signal statistics
# -----------------------------
signal_stats_lookup = {}

if not signal_stats_df.empty:
    signal_col = find_first_existing_column(signal_stats_df, ["Signal", "Pattern"])
    trades_col = find_first_existing_column(signal_stats_df, ["Trades", "EvidenceCount"])
    stats_winrate_col = find_first_existing_column(signal_stats_df, ["WinRate", "AvgWinRate"])
    stats_avgreturn_col = find_first_existing_column(signal_stats_df, ["AverageReturn", "AvgReturn"])

    if signal_col:
        for _, row in signal_stats_df.iterrows():
            signal_name = safe_str(row[signal_col])
            signal_stats_lookup[signal_name] = {
                "Trades": row[trades_col] if trades_col else None,
                "WinRate": row[stats_winrate_col] if stats_winrate_col else None,
                "AvgReturn": row[stats_avgreturn_col] if stats_avgreturn_col else None,
            }


# -----------------------------
# Build research memory rows
# -----------------------------
snapshot_date = datetime.today().strftime("%Y-%m-%d")
memory_rows = []

for _, row in confidence_df.iterrows():
    pattern = safe_str(row["Pattern"])

    # Try to infer the root signal type from the left side of the pattern
    root_signal = pattern.split("|")[0].strip() if "|" in pattern else pattern

    confidence_score = row[confidence_score_col] if confidence_score_col else None
    evidence_count = row[evidence_col] if evidence_col else None
    win_rate = row[winrate_col] if winrate_col else None
    avg_return = row[avgreturn_col] if avgreturn_col else None
    last_seen = row[last_seen_col] if last_seen_col else None
    best_rank = row[best_rank_col] if best_rank_col else None
    worst_rank = row[worst_rank_col] if worst_rank_col else None
    confidence_rank = row[confidence_rank_col] if confidence_rank_col else None

    # Fill missing evidence/win rate/avg return from signal_statistics if possible
    if pd.isna(evidence_count) and root_signal in signal_stats_lookup:
        evidence_count = signal_stats_lookup[root_signal].get("Trades")

    if pd.isna(win_rate) and root_signal in signal_stats_lookup:
        win_rate = signal_stats_lookup[root_signal].get("WinRate")

    if pd.isna(avg_return) and root_signal in signal_stats_lookup:
        avg_return = signal_stats_lookup[root_signal].get("AvgReturn")

    stability_status = "UNKNOWN"
    stability_rank = None
    if pattern in stability_lookup:
        stability_status = stability_lookup[pattern].get("StabilityStatus", "UNKNOWN")
        stability_rank = stability_lookup[pattern].get("StabilityRank")

    decay_status = "UNKNOWN"
    if pattern in decay_lookup:
        decay_status = decay_lookup[pattern].get("DecayStatus", "UNKNOWN")

    summary = (
        f"Pattern {pattern} has confidence score {round_or_none(confidence_score)}; "
        f"evidence count {evidence_count if not pd.isna(evidence_count) else 'UNKNOWN'}; "
        f"win rate {round_or_none(win_rate, 2) if win_rate is not None and not pd.isna(win_rate) else 'UNKNOWN'}; "
        f"average return {round_or_none(avg_return)}; "
        f"stability {stability_status}; "
        f"decay status {decay_status}."
    )

    memory_rows.append({
        "SnapshotDate": snapshot_date,
        "Domain": "Markets",
        "Topic": "Signal Discovery",
        "Pattern": pattern,
        "ConfidenceRank": confidence_rank,
        "ConfidenceScore": round_or_none(confidence_score),
        "EvidenceCount": None if pd.isna(evidence_count) else evidence_count,
        "StabilityRank": None if pd.isna(stability_rank) else stability_rank,
        "StabilityStatus": stability_status,
        "DecayStatus": decay_status,
        "WinRate": round_or_none(win_rate, 2) if win_rate is not None else None,
        "AvgReturn": round_or_none(avg_return),
        "BestRank": None if pd.isna(best_rank) else best_rank,
        "WorstRank": None if pd.isna(worst_rank) else worst_rank,
        "LastSeen": None if pd.isna(last_seen) else last_seen,
        "Summary": summary
    })

new_memory_df = pd.DataFrame(memory_rows)

if new_memory_df.empty:
    print("No research memory rows were created.")
    raise SystemExit(1)


# -----------------------------
# Merge with existing memory
# -----------------------------
if memory_path.exists() and memory_path.stat().st_size > 0:
    old_memory_df = pd.read_csv(memory_path)
    memory_df = pd.concat([old_memory_df, new_memory_df], ignore_index=True)
else:
    memory_df = new_memory_df.copy()

# Remove same-day duplicate snapshots for same pattern
memory_df = memory_df.drop_duplicates(
    subset=["SnapshotDate", "Domain", "Topic", "Pattern"],
    keep="last"
).reset_index(drop=True)

# Save
memory_df.to_csv(memory_path, index=False)

print("Research memory saved to data/research_memory.csv")
print(memory_df.tail(10))