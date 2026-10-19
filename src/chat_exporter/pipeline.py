"""The whole export job, from opening the browser to saving the file.

This file knows nothing about windows or buttons. The GUI (or a test
script) calls run_export() and passes in two small helper functions:
  progress(text)   - called to report what is happening
  wait_for_user()  - called when the user must log in / open a chat
                     and then confirm
"""

from pathlib import Path  # cross-platform file paths
from typing import Callable  # type hint for "a function passed as an argument"

from chat_exporter.adapters import chatgpt, claude, gemini
from chat_exporter.browsers.chromium import BrowserSession
from chat_exporter.exporters.docx_export import export_docx
from chat_exporter.exporters.pdf import export_pdf
from chat_exporter.paths import build_output_path
from chat_exporter.settings import OutputFormat, Service, Settings

# Start page of every supported service.
SERVICE_URLS = {
    Service.CLAUDE: "https://claude.ai",
    Service.GEMINI: "https://gemini.google.com",
    Service.CHATGPT: "https://chatgpt.com",
}

# The function that reads a chat for each service.
READERS = {
    Service.CLAUDE: claude.read_chat,
    Service.GEMINI: gemini.read_chat,
    Service.CHATGPT: chatgpt.read_chat,
}


def run_export(
    settings: Settings,
    progress: Callable[[str], None],
    wait_for_user: Callable[[], None],
) -> list[Path]:
    """Run the export and return the paths of the created files."""
    # Fail early, with a clear message, for things we have not built yet.
    if settings.service not in SERVICE_URLS:
        raise NotImplementedError(f"{settings.service.name.title()} is not supported yet.")


    progress("Opening the browser...")
    with BrowserSession(settings.browser.value) as page:
        page.goto(SERVICE_URLS[settings.service])

        # Pause until the user has logged in and opened the chat.
        progress("Log in if needed, open the chat you want, then continue.")
        wait_for_user()

        progress("Reading the chat (this can take a while for long chats)...")
        chat = READERS[settings.service](page)

    progress(f"Found {len(chat.messages)} messages. Creating the file(s)...")

    # Which file types to create from this one chat.
    wanted = (
        [OutputFormat.PDF, OutputFormat.DOCX]
        if settings.output_format == OutputFormat.BOTH
        else [settings.output_format]
    )

    created: list[Path] = []
    for output_format in wanted:
        extension = output_format.value  # "pdf" or "docx"
        output_path = build_output_path(chat.title, extension)
        if output_format == OutputFormat.PDF:
            export_pdf(chat, output_path, settings.language)
        else:
            export_docx(chat, output_path, settings.language)
        created.append(output_path)

    names = ", ".join(path.name for path in created)
    progress(f"Done: {names}")
    return created

    progress(f"Done: {output_path}")
    return output_path