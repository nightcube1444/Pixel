from pathlib import Path
import pandas as pd

LIVE_MATCHES = Path(
    "data/live_pattern_matches.csv"
)

OUTPUT_FILE = Path(
    "data/research_teacher_notes.csv"
)


def generate_note(row):

    trust = row["TrustLevel"]
    signal = row["PrimarySignal"]
    ticker = row["Ticker"]

    if trust == "INSTITUTIONAL":
        recommendation = (
            "Highest confidence research pattern."
        )

    elif trust == "HIGH":
        recommendation = (
            "Strong research candidate. "
            "Paper trade first."
        )

    elif trust == "MEDIUM":
        recommendation = (
            "Needs additional evidence."
        )

    elif trust == "LOW":
        recommendation = (
            "Weak evidence. Research only."
        )

    else:
        recommendation = (
            "Do not trust yet."
        )

    note = f"""
{ticker} RESEARCH NOTE

Signal: {signal}

Trust Level: {trust}

Pattern:
{row['Pattern']}

Research Evidence:
Trades Observed = {int(row['Trades'])}

Confidence Score:
{round(row['ConfidenceScore'],2)}

Historical Win Rate:
{round(row['WinRate'],2)}%

Alpha Score:
{round(row['AlphaScore'],2)}

Interpretation:
This pattern has been observed repeatedly
in historical market data and passed
through the validation pipeline.

Recommendation:
{recommendation}
"""

    return note.strip()


def main():

    print("\nRESEARCH TEACHER ENGINE\n")

    df = pd.read_csv(
        LIVE_MATCHES
    )

    df["ResearchNote"] = df.apply(
        generate_note,
        axis=1
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    for note in df["ResearchNote"].head(5):
        print("=" * 60)
        print(note)
        print()

    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()