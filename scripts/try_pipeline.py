"""Developer helper: run the full pipeline from the terminal.

Usage:  python scripts/try_pipeline.py [pdf|docx]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chat_exporter.pipeline import run_export  # noqa: E402
from chat_exporter.settings import OutputFormat, Settings  # noqa: E402


def main() -> None:
    choice = sys.argv[1] if len(sys.argv) > 1 else "pdf"
    settings = Settings(output_format=OutputFormat(choice))

    run_export(
        settings,
        progress=print,  # just print every message in the terminal
        wait_for_user=lambda: input("Press Enter when the chat is open... "),
    )


if __name__ == "__main__":
    main()