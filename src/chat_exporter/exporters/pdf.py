"""Turns a Chat into a PDF file using a headless Chromium browser.

"Headless" means the browser runs invisibly in the background. We feed
it the clean HTML from html_builder and ask it to print that page to PDF.
"""

from pathlib import Path  # modern, cross-platform way to work with file paths

from playwright.sync_api import sync_playwright  # lets Python control a browser

from chat_exporter.exporters.html_builder import build_html  # our HTML page maker
from chat_exporter.models import Chat  # our shared chat structure


def export_pdf(chat: Chat, output_path: Path) -> Path:
    """Write the chat to a PDF file and return the path of that file."""
    html = build_html(chat)  # step 1: chat -> HTML text

    # "with" opens Playwright and guarantees it is shut down properly
    # at the end, even if an error happens in the middle.
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
             channel="chrome",   # use the Chrome installed on this computer
             headless=True,      # invisible browser
        )
        try:
            page = browser.new_page()  # a blank browser tab

            # Put our HTML directly into the tab (no website, no internet needed).
            page.set_content(html, wait_until="load")

            # Ask the browser to "print" the tab into a PDF file.
            page.pdf(
                path=str(output_path),   # where to save the file
                format="A4",             # paper size
                print_background=True,   # keep the colored message boxes
                margin={"top": "15mm", "bottom": "15mm",
                        "left": "15mm", "right": "15mm"},
            )
        finally:
            # Always close the browser, whether the export worked or not.
            browser.close()

    return output_path