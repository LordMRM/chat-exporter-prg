"""Developer helper: read the open Claude chat and export PDF + DOCX."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chat_exporter.adapters.claude import read_chat  # noqa: E402
from chat_exporter.browsers.chromium import BrowserSession  # noqa: E402
from chat_exporter.exporters.docx_export import export_docx  # noqa: E402
from chat_exporter.exporters.pdf import export_pdf  # noqa: E402
from chat_exporter.models import ChatLanguage  # noqa: E402
from chat_exporter.paths import build_output_path  # noqa: E402


def main() -> None:
    with BrowserSession("chrome") as page:
        page.goto("https://claude.ai")
        input("Open a SHORT chat from the sidebar, wait until it loads, then press Enter... ")
        chat = read_chat(page)

    print(f"Title: {chat.title}")
    print(f"Messages found: {len(chat.messages)}")

    pdf_path = export_pdf(chat, build_output_path(chat.title, "pdf"), ChatLanguage.MIXED)
    docx_path = export_docx(chat, build_output_path(chat.title, "docx"), ChatLanguage.MIXED)
    print("Saved:", pdf_path)
    print("Saved:", docx_path)


if __name__ == "__main__":
    main()