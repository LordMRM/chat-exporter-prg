"""The whole export job, from opening the browser to saving the file.

This file knows nothing about windows or buttons. The GUI (or a test
script) calls run_export() and passes in two small helper functions:
  progress(text)   - called to report what is happening
  wait_for_user()  - called when the user must log in / open a chat
                     and then confirm
"""

from pathlib import Path  # cross-platform file paths
from typing import Callable  # type hint for "a function passed as an argument"

from chat_exporter.adapters.claude import read_chat
from chat_exporter.browsers.chromium import BrowserSession
from chat_exporter.exporters.docx_export import export_docx
from chat_exporter.exporters.pdf import export_pdf
from chat_exporter.paths import build_output_path
from chat_exporter.settings import BrowserChoice, OutputFormat, Service, Settings

# Start page of every supported service. Gemini and ChatGPT come later.
SERVICE_URLS = {Service.CLAUDE: "https://claude.ai"}


def run_export(
    settings: Settings,
    progress: Callable[[str], None],
    wait_for_user: Callable[[], None],
) -> Path:
    """Run the export and return the path of the created file."""
    # Fail early, with a clear message, for things we have not built yet.
    if settings.service not in SERVICE_URLS:
        raise NotImplementedError(f"{settings.service.name.title()} is not supported yet.")
    if settings.browser == BrowserChoice.FIREFOX:
        raise NotImplementedError("Firefox is not supported yet.")

    progress("Opening the browser...")
    with BrowserSession(settings.browser.value) as page:
        page.goto(SERVICE_URLS[settings.service])

        # Pause until the user has logged in and opened the chat.
        progress("Log in if needed, open the chat you want, then continue.")
        wait_for_user()

        progress("Reading the chat (this can take a while for long chats)...")
        chat = read_chat(page)

    progress(f"Found {len(chat.messages)} messages. Creating the file...")
    extension = settings.output_format.value  # "pdf" or "docx"
    output_path = build_output_path(chat.title, extension)

    if settings.output_format == OutputFormat.PDF:
        export_pdf(chat, output_path, settings.language)
    else:
        export_docx(chat, output_path, settings.language)

    progress(f"Done: {output_path}")
    return output_path