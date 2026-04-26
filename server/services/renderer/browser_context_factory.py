from playwright.sync_api import Browser


def create_browser_context(browser: Browser):
    return browser.new_context(
        ignore_https_errors=False,
        viewport={"width": 1920, "height": 1080},
    )
