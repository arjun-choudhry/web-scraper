from pathlib import Path
import zipfile

from server.services.archive.zip_builder import build_zip_archive


def test_build_zip_archive(tmp_path: Path):
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    (pdf_dir / "a.pdf").write_bytes(b"first")
    (pdf_dir / "b.pdf").write_bytes(b"second")

    zip_path = tmp_path / "bundle.zip"
    build_zip_archive(pdf_dir, zip_path)

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["a.pdf", "b.pdf"]
