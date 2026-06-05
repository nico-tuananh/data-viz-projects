"""
Launcher for the US-China Tariff Dashboard (Shiny).

Run:
    python main.py              # launches dashboard on port 8004
    python main.py --port 8005  # custom port

Data pipeline:
    python scripts/setup_bigquery.py       # verify BigQuery credentials
    python scripts/data_collection.py      # collect + preprocess GDELT data
    python forecasting/forecast_models.py  # run forecast models
"""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the US-China Tariff Shiny Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8004, help="Port (default: 8004)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on file changes")
    args = parser.parse_args()

    cmd = [
        sys.executable, "-m", "shiny", "run",
        "shiny_app/app.py",
        "--host", args.host,
        "--port", str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")

    print(f"Starting dashboard at http://{args.host}:{args.port}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
