"""Developer helper: find where chat text lives in the ChatGPT page.

It prints only tag names and attributes around ONE word you choose
from the chat, never the chat text itself.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chat_exporter.browsers.chromium import BrowserSession  # noqa: E402

# Runs inside the page: counts our selectors and shows the ancestors
# of the first text node that contains the chosen word.
JS = """
(word) => {
  const info = {
    url: location.href,
    roles: document.querySelectorAll('[data-message-author-role]').length,
    turns: document.querySelectorAll('[data-testid^="conversation-turn"]').length,
    articles: document.querySelectorAll('article').length,
    sections: document.querySelectorAll('section').length,
    iframes: document.querySelectorAll('iframe').length,
    chain: [],
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (node.nodeValue.includes(word)) {
      let el = node.parentElement;
      for (let i = 0; el && i < 10; i++) {
        const attrs = [...el.attributes]
          .filter(a => a.name !== 'class' && a.name !== 'style')
          .map(a => a.name + '=' + a.value.slice(0, 40));
        info.chain.push(
          el.tagName.toLowerCase() +
          ' class=' + (el.className || '').toString().slice(0, 40) +
          ' ' + attrs.join(' ')
        );
        el = el.parentElement;
      }
      break;
    }
  }
  return info;
}
"""


def main() -> None:
    with BrowserSession("chrome") as page:
        page.goto("https://chatgpt.com")
        input("Open the chat, wait until it is fully loaded (do NOT press F5 now), then press Enter... ")
        word = input("Type one word that appears in a message of this chat: ").strip()

        page.wait_for_load_state("load")
        print("Frames in page:", len(page.frames))
        for number, frame in enumerate(page.frames):
            try:
                info = frame.evaluate(JS, word)
            except Exception as error:  # frame not readable
                print(f"frame {number}: error {error}")
                continue
            print(f"--- frame {number}: {info['url'][:80]}")
            for key in ("roles", "turns", "articles", "sections", "iframes"):
                print(f"  {key}: {info[key]}")
            for line in info["chain"]:
                print("   ", line)


if __name__ == "__main__":
    main()