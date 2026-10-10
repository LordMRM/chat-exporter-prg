"""Developer helper: open a page in our browser and save its HTML.

Usage:  python scripts/inspect_page.py https://claude.ai

It is NOT part of the final program. We only use it to study how a
website structures its chat messages, so we can write a correct adapter.
"""

import sys  # sys.argv holds the words typed after the program name
from pathlib import Path  # cross-platform file paths

# This script lives outside the package, so we tell Python where "src" is.
# __file__ = this file; .parent = scripts/; .parent.parent = project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chat_exporter.browsers.chromium import BrowserSession  # noqa: E402


def main() -> None:
    # sys.argv[0] is the script name, sys.argv[1] is the first argument.
    url = sys.argv[1] if len(sys.argv) > 1 else "https://claude.ai"

    with BrowserSession("chrome") as page:
        page.goto(url)

        # Pause here. Meanwhile the user logs in and opens a chat.
        input("Log in, open a SHORT test chat, then press Enter here... ")

        html = page.content()  # the page's current HTML as one big string
        output = Path("page_dump.html")
        output.write_text(html, encoding="utf-8")

        print(f"Saved {len(html)} characters to {output.resolve()}")
        print("Address of the page:", page.url)


if __name__ == "__main__":
    main()