from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from server.services.convert_job import get_job

router = APIRouter(tags=["download"])


@router.get("/jobs/{job_id}/download")
def download_result(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=409, detail="Job is not completed yet")

    output_path = Path(job.output_path)
    
    # Clean up the job directory after download
    def cleanup_after_download():
        try:
            if output_path.exists():
                job_dir = output_path.parent
                if job_dir.exists() and job_dir != output_path.parent.parent:
                    import shutil
                    shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass
    
    response = FileResponse(
        path=job.output_path,
        media_type=job.output_media_type or "application/octet-stream",
        filename=job.output_filename or f"{job_id}.bin",
    )
    response.background = cleanup_after_download
    
    return response
