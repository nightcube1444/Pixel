import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

VENV_PYTHON = BASE_DIR / "venv" / "bin" / "python"


def run_python_script(script_name):

    script_path = BASE_DIR / "scripts" / script_name

    if not script_path.exists():
        print(f"\nMissing script: {script_name}")
        return

    print(f"\nRunning: {script_name}")
    print("-" * 50)

    result = subprocess.run(
        [str(VENV_PYTHON), str(script_path)],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)


def run_pipeline():
    run_python_script("run_pipeline.py")


def run_download_data():
    run_python_script("download_data.py")


def run_fetch_news():
    run_python_script("fetch_news.py")


def run_signal_engine():
    run_python_script("signal_engine.py")


def run_research_summary():
    run_python_script("research_summary_engine.py")


def run_system_health():
    run_python_script("system_health_check.py")


def show_menu():

    print("\nMARKET INTELLIGENCE OS")
    print("=" * 50)

    print("1. Run Full Pipeline")
    print("2. Download Market Data")
    print("3. Fetch News")
    print("4. Run Signal Engine")
    print("5. Generate Research Summary")
    print("6. System Health Check")
    print("0. Exit")


def main():

    while True:

        show_menu()

        choice = input("\nChoose option: ").strip()

        if choice == "1":
            run_pipeline()

        elif choice == "2":
            run_download_data()

        elif choice == "3":
            run_fetch_news()

        elif choice == "4":
            run_signal_engine()

        elif choice == "5":
            run_research_summary()

        elif choice == "6":
            run_system_health()

        elif choice == "0":
            print("\nGoodbye.")
            break

        else:
            print("\nInvalid option.")


if __name__ == "__main__":
    main()