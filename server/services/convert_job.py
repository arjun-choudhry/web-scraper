from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import threading
import uuid

from server.schemas.convert import JobStatus, UrlResult
from server.services.archive.zip_builder import build_zip_archive
from server.services.auth.auth_strategy import AuthStrategy, NoAuthStrategy
from server.services.renderer.playwright_pdf import render_url_to_pdf


ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    urls: list[str]
    created_at: datetime
    results: list[UrlResult] = field(default_factory=list)
    error: str | None = None
    output_path: str | None = None
    output_filename: str | None = None
    output_media_type: str | None = None
    auth_strategy: AuthStrategy | None = None


_jobs: dict[str, JobRecord] = {}
_lock = threading.Lock()


def create_job(urls: list[str], auth_strategy: AuthStrategy | None = None) -> JobRecord:
    record = JobRecord(
        job_id=uuid.uuid4().hex,
        status="pending",
        urls=urls,
        created_at=datetime.now(timezone.utc),
        auth_strategy=auth_strategy or NoAuthStrategy(),
    )
    with _lock:
        _jobs[record.job_id] = record
    return record


def get_job(job_id: str) -> JobRecord | None:
    with _lock:
        return _jobs.get(job_id)


def process_job(job_id: str) -> None:
    record = get_job(job_id)
    if record is None:
        return

    with _lock:
        record.status = "running"

    job_dir = ARTIFACTS_DIR / job_id
    pdf_dir = job_dir / "pdf"
    zip_path = job_dir / "bundle.zip"

    results: list[UrlResult] = []
    try:
        for index, url in enumerate(record.urls, start=1):
            try:
                filename = render_url_to_pdf(
                    url=url,
                    output_dir=pdf_dir,
                    index=index,
                    auth_strategy=record.auth_strategy,
                )
                results.append(UrlResult(url=url, status="success", filename=filename))
            except Exception as exc:  # pragma: no cover
                results.append(UrlResult(url=url, status="failed", error=str(exc)))

        successful_files = [result.filename for result in results if result.status == "success" and result.filename]
        if not successful_files:
            raise RuntimeError("No PDFs were generated successfully for this job.")

        if len(record.urls) == 1 and len(successful_files) == 1:
            single_filename = successful_files[0]
            output_path = pdf_dir / single_filename
            output_filename = single_filename
            output_media_type = "application/pdf"
        else:
            build_zip_archive(pdf_dir, zip_path)
            output_path = zip_path
            output_filename = f"{job_id}.zip"
            output_media_type = "application/zip"

        with _lock:
            record.results = results
            record.status = "completed"
            record.output_path = str(output_path)
            record.output_filename = output_filename
            record.output_media_type = output_media_type
    except Exception as exc:  # pragma: no cover
        with _lock:
            record.results = results
            record.status = "failed"
            record.error = str(exc)
