#!/usr/bin/env python3
"""
Helper script to capture cookies from a signed-in browser session.

Usage:
1. Run this script: python scripts/capture_cookies.py
2. A browser window will open - sign in to the site you want to capture
3. Once signed in, close the browser window
4. Cookies will be saved to auth_cookies.json

You can then use this cookie file with the popup auth option.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def capture_cookies(auth_url: str, output_file: str = "auth_cookies.json") -> None:
    """Open browser, let user sign in, then save cookies."""
    output_path = Path(output_file)
    
    # Ensure URL has protocol
    if not auth_url.startswith(("http://", "https://")):
        auth_url = f"https://{auth_url}"
    
    with sync_playwright() as p:
        # Launch with more realistic settings to avoid security blocks
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        
        # Create context with realistic user agent
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        
        # Add some basic cookies to make the browser look more legitimate
        context.add_cookies([
            {
                "name": "test_cookie",
                "value": "1",
                "domain": auth_url.split("/")[2] if "/" in auth_url[8:] else auth_url,
                "path": "/",
            }
        ])
        
        page = context.new_page()
        
        print(f"Opening {auth_url} for authentication...")
        print("Sign in to the site, then close the browser when done.")
        
        page.goto(auth_url, wait_until="networkidle")
        
        # Wait for user to manually close the browser
        input("Press Enter after you've signed in and want to save cookies...")
        
        # Save cookies
        cookies = context.cookies()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(cookies, f, indent=2)
        
        print(f"Cookies saved to {output_path}")
        
        context.close()
        browser.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture cookies from a signed-in session")
    parser.add_argument("url", help="URL to open for authentication")
    parser.add_argument("-o", "--output", default="auth_cookies.json", help="Output file for cookies")
    
    args = parser.parse_args()
    capture_cookies(args.url, args.output)
