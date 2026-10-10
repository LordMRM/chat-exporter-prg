"""Reads a conversation from the claude.ai website.

claude.ai only keeps the message rows near the visible area in the page
(long chats are loaded lazily). So we scroll through the chat step by
step and collect every row we see, using its fixed row number
(data-index) to avoid duplicates and to restore the correct order.
"""

import time  # short pauses so the page can load new rows

from playwright.sync_api import Page

from chat_exporter.models import Chat, Message, Role

ROW_SELECTOR = '[data-testid="transcript-row"]'
TEXT_SELECTOR = "p, li, pre, h1, h2, h3, h4, h5, h6"

SCROLL_FRACTION = 0.8   # scroll 80% of the visible height per step
PAUSE_SECONDS = 0.4     # wait after each scroll for rows to load
MAX_STEPS = 2000        # safety limit so we can never loop forever
MAX_PASSES = 3          # how many full scroll attempts before giving up
MAX_TOP_ATTEMPTS = 40   # safety limit for the "reach the top" phase
TOP_PAUSE_SECONDS = 1.0 # wait after each jump to the top

# JavaScript that runs inside the page. It finds the scrolling element
# (the nearest scrollable ancestor of the first row) and marks it, so
# later calls can find it again quickly.
MARK_SCROLLER_JS = """
() => {
  const row = document.querySelector('[data-testid="transcript-row"]');
  let node = row;
  while (node) {
    const overflow = getComputedStyle(node).overflowY;
    if (/(auto|scroll)/.test(overflow) && node.scrollHeight > node.clientHeight) {
      node.setAttribute('data-exporter-scroller', '1');
      return true;
    }
    node = node.parentElement;
  }
  return false;
}
"""

SCROLLER = '[data-exporter-scroller="1"]'

# Reads the scrolling element's current numbers.
METRICS_JS = """
(el) => ({
  top: el.scrollTop,
  height: el.clientHeight,
  total: el.scrollHeight,
})
"""

# Reads every row currently in the page. Returns plain data (no live
# elements), so nothing can go stale while the page keeps changing.
COLLECT_JS = """
(selectors) => {
  const rows = [];
  for (const row of document.querySelectorAll(selectors.row)) {
    // Skip rows whose reply is still being written.
    if (row.getAttribute('data-perf-row-streaming') === 'true') continue;

    const blocks = [];
    const messages = row.querySelectorAll(
      '[data-testid="user-message"], [data-testid="assistant-message"]'
    );
    for (const message of messages) {
      for (const el of message.querySelectorAll(selectors.text)) {
        if ((el.className || '').toString().includes('sr-only')) continue;
        const text = el.innerText.trim();
        if (text) blocks.push(text);
      }
    }
    rows.push({
      index: parseInt(row.getAttribute('data-index'), 10),
      role: row.getAttribute('data-perf-row'),
      text: blocks.join('\\n\\n'),
    });
  }
  return rows;
}
"""


def collect_visible_rows(page: Page, found: dict, seen: set) -> int:
    """Read the rows now in the page.

    found: row number -> row data (only rows that contain text)
    seen:  row numbers of ALL rows we have ever noticed, even empty ones.
           We use it to detect gaps (rows we scrolled past without reading).
    Returns how many new text rows were found.
    """
    new_rows = 0
    selectors = {"row": ROW_SELECTOR, "text": TEXT_SELECTOR}
    for row in page.evaluate(COLLECT_JS, selectors):
        index = row["index"]
        seen.add(index)
        if not row["text"]:
            continue  # rows without text (spacers, status rows)
        if index not in found:
            new_rows += 1
        found[index] = row  # newer reading replaces older
    return new_rows


def scroll_to_top(page: Page, scroller, found: dict, seen: set) -> None:
    """Jump to the top repeatedly until nothing new appears there."""
    stable_rounds = 0
    last_signature = None
    for _ in range(MAX_TOP_ATTEMPTS):
        scroller.evaluate("el => { el.scrollTop = 0; }")
        time.sleep(TOP_PAUSE_SECONDS)
        collect_visible_rows(page, found, seen)

        metrics = scroller.evaluate(METRICS_JS)
        # If the total height and the lowest row number did not change,
        # the page has probably finished loading the top.
        signature = (metrics["total"], min(seen) if seen else None)
        if signature == last_signature and metrics["top"] <= 2:
            stable_rounds += 1
        else:
            stable_rounds = 0
        last_signature = signature

        if stable_rounds >= 3:
            return
    print("  Warning: could not confirm that we reached the top.")


def scroll_down_pass(page: Page, scroller, found: dict, seen: set) -> None:
    """Scroll from the current position to the bottom, reading as we go."""
    for step_number in range(MAX_STEPS):
        collect_visible_rows(page, found, seen)

        metrics = scroller.evaluate(METRICS_JS)
        at_bottom = metrics["top"] + metrics["height"] >= metrics["total"] - 2
        if at_bottom:
            # Wait a moment: if the page grows, we were not really at the end.
            time.sleep(1.0)
            collect_visible_rows(page, found, seen)
            again = scroller.evaluate(METRICS_JS)
            if again["total"] == metrics["total"]:
                return
            continue

        if step_number % 20 == 0:
            print(
                f"  scrolling... position {metrics['top']}/{metrics['total']}, "
                f"rows with text so far: {len(found)}"
            )

        step = int(metrics["height"] * SCROLL_FRACTION)
        scroller.evaluate(f"el => {{ el.scrollTop += {step}; }}")
        time.sleep(PAUSE_SECONDS)


def find_gaps(seen: set) -> list[int]:
    """Return the row numbers missing between the first and last seen row."""
    if not seen:
        return []
    return [i for i in range(min(seen), max(seen) + 1) if i not in seen]


def read_chat(page: Page) -> Chat:
    """Scroll through the open chat and return all of its messages."""
    title = page.title().removesuffix(" - Claude").strip() or "Claude chat"

    page.wait_for_selector(ROW_SELECTOR, timeout=15000)
    if not page.evaluate(MARK_SCROLLER_JS):
        raise RuntimeError("Could not find the scrolling area of the chat.")

    scroller = page.locator(SCROLLER)
    found: dict[int, dict] = {}
    seen: set[int] = set()

    for attempt in range(1, MAX_PASSES + 1):
        print(f"Pass {attempt}: going to the top...")
        scroll_to_top(page, scroller, found, seen)
        print(f"  top reached, first row number: {min(seen) if seen else '?'}")
        scroll_down_pass(page, scroller, found, seen)

        gaps = find_gaps(seen)
        starts_at_zero = bool(seen) and min(seen) == 0
        print(
            f"  pass {attempt} done: rows seen {len(seen)}, "
            f"with text {len(found)}, gaps {len(gaps)}, starts at 0: {starts_at_zero}"
        )
        if not gaps and starts_at_zero:
            break  # complete
    else:
        print("Warning: the chat may be incomplete.")
        if gaps:
            print("  missing row numbers (first 30):", gaps[:30])

    messages = []
    for index in sorted(found):  # restore the original order
        row = found[index]
        role = Role.USER if row["role"] == "human" else Role.ASSISTANT
        messages.append(Message(role, row["text"]))

    return Chat(title=title, source="claude", messages=messages)