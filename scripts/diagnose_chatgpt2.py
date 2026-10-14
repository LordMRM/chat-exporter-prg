"""Developer helper: list the new-style turn markers of ChatGPT.

Prints only attribute names/values and text LENGTHS, never chat text.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chat_exporter.browsers.chromium import BrowserSession  # noqa: E402

JS = """
() => {
  const out = [];
  for (const el of document.querySelectorAll('[data-content-search-unit-key]')) {
    out.push({
      key: el.getAttribute('data-content-search-unit-key'),
      messageIds: el.getAttribute('data-chatgpt-search-message-ids'),
      state: (el.querySelector('[data-talvt-turn-state]') || {}).dataset
        ? el.querySelector('[data-talvt-turn-state]').dataset.talvtTurnState : null,
      textLength: el.innerText.length,
      hasMarkdown: !!el.querySelector('[data-markdown-text-style]'),
      markdownStyle: (el.querySelector('[data-markdown-text-style]') || {}).dataset
        ? el.querySelector('[data-markdown-text-style]').dataset.markdownTextStyle : null,
    });
  }
  const scrollers = [];
  let node = document.querySelector('[data-content-search-unit-key]');
  while (node) {
    if (/(auto|scroll)/.test(getComputedStyle(node).overflowY) &&
        node.scrollHeight > node.clientHeight) {
      scrollers.push(node.tagName + ' ' + node.scrollHeight + '/' + node.clientHeight);
    }
    node = node.parentElement;
  }
  return { units: out, scrollers };
}
"""


def main() -> None:
    with BrowserSession("chrome") as page:
        page.goto("https://chatgpt.com")
        input("Open a chat with at least 3 messages, wait until loaded, then press Enter... ")
        result = page.evaluate(JS)
        print("scrollers:", result["scrollers"])
        print("units:", len(result["units"]))
        for unit in result["units"][:12]:
            print(unit)


if __name__ == "__main__":
    main()