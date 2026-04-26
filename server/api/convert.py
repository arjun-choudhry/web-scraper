from fastapi import APIRouter, BackgroundTasks, HTTPException

from server.schemas.convert import ConvertRequest, JobResponse
from server.services.auth.auth_strategy import (
    BrowserSessionAuthStrategy,
    CookieAuthStrategy,
    PopupAuthStrategy,
)
from server.services.convert_job import create_job, get_job, process_job
from server.validation.url_list import parse_urls, validate_public_urls

router = APIRouter(tags=["convert"])


@router.post("/convert", response_model=JobResponse)
def start_conversion(payload: ConvertRequest, background_tasks: BackgroundTasks):
    parsed = parse_urls(payload.urls, payload.url_text)
    try:
        validated = validate_public_urls(parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Determine auth strategy based on request
    auth_strategy = None
    if payload.auth_type == "cookie" and payload.auth_cookie_file:
        auth_strategy = CookieAuthStrategy(cookie_file=payload.auth_cookie_file)
    elif payload.auth_type == "popup" and payload.auth_popup_url:
        auth_strategy = PopupAuthStrategy(auth_url=payload.auth_popup_url)
    elif payload.auth_type == "browser_session" and payload.auth_cookie_file:
        auth_strategy = BrowserSessionAuthStrategy(cookie_file=payload.auth_cookie_file)

    job = create_job(validated, auth_strategy=auth_strategy)
    background_tasks.add_task(process_job, job.job_id)
    return JobResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    download_path = f"/api/jobs/{job_id}/download" if job.status == "completed" else None
    download_type = None
    if job.status == "completed":
        if job.output_media_type == "application/pdf":
            download_type = "pdf"
        elif job.output_media_type == "application/zip":
            download_type = "zip"

    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        results=job.results,
        error=job.error,
        download_path=download_path,
        download_type=download_type,
    )
