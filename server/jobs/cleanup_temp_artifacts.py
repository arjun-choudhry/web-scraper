from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil


def cleanup_old_artifacts(base_dir: Path, max_age_hours: int = 3) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    if not base_dir.exists():
        return

    for item in base_dir.iterdir():
        modified = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
