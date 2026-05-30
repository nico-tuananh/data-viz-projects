"""Data collection refresh endpoint."""
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/api/data", tags=["data_refresh"])


def _run_data_collection():
    """Background task: re-run data_collection.py to fetch fresh GDELT data."""
    project_root = Path(__file__).parent.parent.parent
    script = project_root / "backend" / "data_collection.py"
    env = os.environ.copy()

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(project_root / "backend"),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        print("[data_refresh] collection completed successfully")
        if result.stdout:
            print(result.stdout[-2000:])  # tail of stdout
    except subprocess.CalledProcessError as exc:
        print(f"[data_refresh] collection failed: {exc.stderr}")
        raise


@router.post("/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """Trigger a background data collection from BigQuery. Returns immediately."""
    background_tasks.add_task(_run_data_collection)
    return {"status": "started"}
