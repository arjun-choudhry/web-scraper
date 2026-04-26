from dataclasses import dataclass
from typing import Protocol


class AuthStrategy(Protocol):
    def apply(self, page) -> None:
        """Apply auth/session state to a newly created page."""


@dataclass(slots=True)
class NoAuthStrategy:
    def apply(self, page) -> None:
        return
