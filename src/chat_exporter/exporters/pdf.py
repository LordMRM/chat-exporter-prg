"""Turns a Chat into a PDF file using a headless Chromium browser.

"Headless" means the browser runs invisibly in the background. We feed
it the clean HTML from html_builder and ask it to print that page to PDF.
"""

from pathlib import Path  # modern, cross-platform way to work with file paths

from playwright.sync_api import sync_playwright  # lets Python control a browser

from chat_exporter.exporters.html_builder import build_html  # our HTML page maker
from chat_exporter.models import Chat, ChatLanguage  # our shared structures

def launch_available_chromium(playwright):
    """Start an invisible Chromium browser: Chrome first, then Edge.

    PDF creation only needs *some* Chromium-based browser installed.
    """
    last_error = None
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch(channel=channel, headless=True)
        except Exception as error:  # this browser is not installed
            last_error = error
    raise RuntimeError(
        "PDF export needs Google Chrome or Microsoft Edge installed."
    ) from last_error

def export_pdf(
    chat: Chat,
    output_path: Path,
    language: ChatLanguage = ChatLanguage.ENGLISH,
) -> Path:
    """Write the chat to a PDF file and return the path of that file."""
    html = build_html(chat, language)  # step 1: chat -> HTML text

    # "with" opens Playwright and guarantees it is shut down properly
    # at the end, even if an error happens in the middle.
    with sync_playwright() as playwright:
        browser = launch_available_chromium(playwright)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm",
                        "left": "15mm", "right": "15mm"},
            )
        finally:
            # Always close the browser, whether the export worked or not.
            browser.close()

    return output_path