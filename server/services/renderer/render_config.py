from dataclasses import dataclass


@dataclass(slots=True)
class RenderConfig:
    navigation_timeout_ms: int = 45000
    page_load_state: str = "networkidle"
    pdf_format: str = "A4"
    print_background: bool = True
