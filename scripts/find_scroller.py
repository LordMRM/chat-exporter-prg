"""Developer helper: find which element scrolls the chat."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chat_exporter.browsers.chromium import BrowserSession  # noqa: E402

# Runs inside the page: walks up from a message row and reports every
# ancestor that can scroll vertically.
JS = """
() => {
  const row = document.querySelector('[data-testid="transcript-row"]');
  const found = [];
  let node = row;
  while (node) {
    const style = getComputedStyle(node);
    const scrolls = /(auto|scroll)/.test(style.overflowY);
    if (scrolls && node.scrollHeight > node.clientHeight) {
      found.push({
        tag: node.tagName,
        testid: node.getAttribute('data-testid'),
        className: (node.className || '').toString().slice(0, 80),
        scrollHeight: node.scrollHeight,
        clientHeight: node.clientHeight,
        scrollTop: node.scrollTop,
      });
    }
    node = node.parentElement;
  }
  return found;
}
"""


def main() -> None:
    with BrowserSession("chrome") as page:
        page.goto("https://claude.ai")
        input("Open the LONG chat, wait until it loads, then press Enter... ")
        for item in page.evaluate(JS):
            print(item)


if __name__ == "__main__":
    main()
