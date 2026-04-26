from playwright.sync_api import Browser


from playwright.sync_api import Browser


def create_browser_context(browser: Browser):
    return browser.new_context(
        ignore_https_errors=False,
        viewport={"width": 1920, "height": 2160},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
