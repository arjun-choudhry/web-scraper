from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.services.convert_job import get_job

router = APIRouter(tags=["download"])


@router.get("/jobs/{job_id}/download")
def download_result(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=409, detail="Job is not completed yet")

    return FileResponse(
        path=job.output_path,
        media_type=job.output_media_type or "application/octet-stream",
        filename=job.output_filename or f"{job_id}.bin",
    )
