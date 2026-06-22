from pathlib import Path
import pandas as pd

EVENTS_PATH = Path(
    "data/pattern_event_validation_results.csv"
)

OUTPUT_PATH = Path(
    "data/pattern_families.csv"
)


def main():

    if not EVENTS_PATH.exists():
        print("Missing event validation file")
        return

    df = pd.read_csv(EVENTS_PATH)

    families = []

    for _, row in df.iterrows():

        pattern = str(row["Pattern"])

        parts = pattern.split("|")

        signal = parts[0] if len(parts) > 0 else ""
        regime = parts[1] if len(parts) > 1 else ""
        volatility = parts[2] if len(parts) > 2 else ""

        family = f"{signal}|{regime}|{volatility}"

        families.append(
            {
                "Ticker": row["Ticker"],
                "Pattern": pattern,
                "PatternFamily": family,
                "WinRate10D": row["WinRate10D"],
                "AvgReturn10D": row["AvgReturn10D"],
                "Events": row["Events"],
            }
        )

    out = pd.DataFrame(families)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    out.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print("\nPATTERN FAMILY ENGINE\n")
    print(out.head(20).to_string(index=False))

    print(
        f"\nSaved -> {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()