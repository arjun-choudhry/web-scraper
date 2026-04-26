import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class AuthStrategy(Protocol):
    def apply(self, page) -> None:
        """Apply auth/session state to a newly created page."""


@dataclass(slots=True)
class NoAuthStrategy:
    def apply(self, page) -> None:
        return


@dataclass(slots=True)
class CookieAuthStrategy:
    """Auth strategy using cookies from a saved session file."""
    cookie_file: str | Path = "auth_cookies.json"

    def __post_init__(self):
        self.cookie_file = Path(self.cookie_file)

    def apply(self, page) -> None:
        """Load and apply saved cookies to the page."""
        if not self.cookie_file.exists():
            return

        try:
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
            page.context.add_cookies(cookies)
        except (json.JSONDecodeError, IOError):
            pass


@dataclass(slots=True)
class PopupAuthStrategy:
    """Auth strategy that opens a popup window for user to sign in."""
    auth_url: str
    cookie_file: str | Path = "auth_cookies.json"

    def __post_init__(self):
        self.cookie_file = Path(self.cookie_file)

    def apply(self, page) -> None:
        """Open popup for auth, then save and apply cookies."""
        # Ensure URL has protocol
        url = self.auth_url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        page.goto(url, wait_until="networkidle")

        # Wait for user to complete auth - they can close the popup when done
        page.evaluate(
            """
            () => {
              return new Promise((resolve) => {
                window.authComplete = resolve;
                const checkBtn = document.querySelector('button, [type="submit"]');
                if (checkBtn) {
                  checkBtn.addEventListener('click', () => {
                    if (window.authComplete) window.authComplete();
                  });
                }
                // Also allow manual completion via window.completeAuth()
                window.completeAuth = () => {
                  if (window.authComplete) window.authComplete();
                };
              });
            }
            """
        )

    def save_cookies(self, page) -> None:
        """Save current page cookies to file for future use."""
        cookies = page.context.cookies()
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cookie_file, "w") as f:
            json.dump(cookies, f, indent=2)


@dataclass(slots=True)
class BrowserSessionAuthStrategy:
    """Auth strategy that uses the current browser session (cookies from existing context)."""
    cookie_file: str | Path = "auth_cookies.json"

    def __post_init__(self):
        self.cookie_file = Path(self.cookie_file)

    def apply(self, page) -> None:
        """Load cookies from file (saved from a signed-in session) and apply to page."""
        if not self.cookie_file.exists():
            return

        try:
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
            page.context.add_cookies(cookies)
        except (json.JSONDecodeError, IOError):
            pass
