from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from server.api.convert import router as convert_router
from server.api.download import router as download_router

app = FastAPI(title="Web to PDF", version="0.1.0")

app.include_router(convert_router, prefix="/api")
app.include_router(download_router, prefix="/api")

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "frontend" / "templates")
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )
