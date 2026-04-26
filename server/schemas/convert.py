from typing import Literal

from pydantic import BaseModel, Field


JobStatus = Literal["pending", "running", "completed", "failed"]


class ConvertRequest(BaseModel):
    urls: list[str] = Field(default_factory=list, description="List of webpage URLs")
    url_text: str | None = Field(
        default=None,
        description="Optional multiline text containing one URL per line",
    )
    auth_type: Literal["none", "cookie", "popup", "browser_session"] = Field(
        default="none",
        description="Authentication type: none, cookie, popup, or browser_session",
    )
    auth_cookie_file: str | None = Field(
        default=None,
        description="Path to file containing saved cookies for cookie auth",
    )
    auth_popup_url: str | None = Field(
        default=None,
        description="URL to open in popup for authentication",
    )


class UrlResult(BaseModel):
    url: str
    status: Literal["success", "failed"]
    filename: str | None = None
    error: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    results: list[UrlResult] = Field(default_factory=list)
    error: str | None = None
    download_path: str | None = None
    download_type: Literal["pdf", "zip"] | None = None
