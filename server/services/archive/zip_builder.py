from pathlib import Path
import zipfile


def build_zip_archive(pdf_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for pdf_file in sorted(pdf_dir.glob("*.pdf")):
            archive.write(pdf_file, arcname=pdf_file.name)
    return zip_path
