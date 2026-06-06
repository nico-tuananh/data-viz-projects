"""Dashboard launcher — python main.py [--port N] [--reload]"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SHINY_APP_DIR = PROJECT_ROOT / "shiny_app"

# Allow imports like: from components.charts import ...
sys.path.insert(0, str(SHINY_APP_DIR))

from shiny_app.app import app
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
