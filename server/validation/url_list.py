from urllib.parse import urlparse


def parse_urls(urls: list[str], url_text: str | None) -> list[str]:
    combined = list(urls)
    if url_text:
        combined.extend(line.strip() for line in url_text.splitlines())

    seen: set[str] = set()
    cleaned: list[str] = []
    for value in combined:
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            cleaned.append(value)
    return cleaned


def validate_public_urls(urls: list[str]) -> list[str]:
    if not urls:
        raise ValueError("Please provide at least one URL.")
    if len(urls) > 30:
        raise ValueError("Maximum 30 URLs per request.")

    normalized: list[str] = []
    for raw in urls:
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Invalid protocol for URL: {raw}")
        if not parsed.netloc:
            raise ValueError(f"Invalid URL: {raw}")
        host = (parsed.hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(f"Local/private hosts are not allowed: {raw}")
        normalized.append(raw)
    return normalized
