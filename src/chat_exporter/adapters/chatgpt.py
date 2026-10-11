"""Reads a conversation from chatgpt.com.

Every message is an element with data-message-author-role ("user" or
"assistant") and a unique data-message-id. ChatGPT only keeps the rows
near the visible area in the page, so we scroll through the chat step
by step and collect every message we see. Each row sits in a container
marked data-testid="conversation-turn-N"; N gives the order and lets us
detect gaps.
"""

import time  # short pauses so the page can load new rows

from playwright.sync_api import Page

from chat_exporter.models import Chat, Message, Role

MESSAGE_SELECTOR = "[data-message-author-role]"

SCROLL_FRACTION = 0.7   # scroll 70% of the visible height per step
PAUSE_SECONDS = 0.5     # wait after each scroll for rows to load
MAX_STEPS = 3000        # safety limit so we can never loop forever
MAX_PASSES = 3          # how many full scroll attempts before giving up
MAX_TOP_ATTEMPTS = 40   # safety limit for the "reach the top" phase
TOP_PAUSE_SECONDS = 1.0 # wait after each jump to the top

# Finds the scrolling element (nearest scrollable ancestor of a message)
# and marks it so later calls can find it again.
MARK_SCROLLER_JS = """
() => {
  let node = document.querySelector('[data-message-author-role]');
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

METRICS_JS = """
(el) => ({ top: el.scrollTop, height: el.clientHeight, total: el.scrollHeight })
"""

# Reads every message currently in the page as plain data.
COLLECT_JS = """
() => {
  const clean = (text) => text.replace(/\\s+/g, ' ').trim();

  const blocksOf = (root) => {
    const out = [];
    const walk = (element) => {
      for (const child of element.children) {
        const tag = child.tagName.toLowerCase();
        if (tag === 'p' || /^h[1-6]$/.test(tag)) {
          const text = clean(child.innerText);
          if (text) out.push(text);
        } else if (tag === 'ul' || tag === 'ol') {
          let number = 0;
          for (const item of child.children) {
            if (item.tagName.toLowerCase() !== 'li') continue;
            number += 1;
            const text = clean(item.innerText);
            if (text) out.push((tag === 'ol' ? number + '. ' : '\\u2022 ') + text);
          }
        } else if (tag === 'pre') {
          const code = child.innerText.replace(/\\s+$/, '');
          if (code) out.push(code);
        } else if (tag === 'table') {
          const lines = ['[[TABLE]]'];
          for (const row of child.querySelectorAll('tr')) {
            const cells = [...row.children].map((cell) => clean(cell.innerText));
            lines.push(cells.join('\\t'));
          }
          out.push(lines.join('\\n'));
        } else if (tag === 'button' || tag === 'svg') {
          continue;
        } else {
          walk(child);
        }
      }
    };
    walk(root);
    return out;
  };

  const turns = [];
  for (const el of document.querySelectorAll('[data-message-author-role]')) {
    const container = el.closest('[data-testid^="conversation-turn-"]');
    const match = container
      ? container.getAttribute('data-testid').match(/(\\d+)$/)
      : null;
    const role = el.getAttribute('data-message-author-role');
    let text;
    if (role === 'user') {
      // User messages are plain text. Keep their line breaks, and turn
      // blank lines into paragraph breaks like everywhere else.
      text = el.innerText.replace(/\\r/g, '').trim();
      text = text.replace(/\\n{2,}/g, '\\n\\n');
    } else {
      text = blocksOf(el).join('\\n\\n');
    }
    turns.push({
      turn: match ? parseInt(match[1], 10) : -1,
      id: el.getAttribute('data-message-id'),
      role,
      text,
    });
  }
  return turns;
}
"""


def collect_visible(page: Page, found: dict, seen: set) -> int:
    """Read the messages now in the page.

    found: message id -> data (only messages that contain text)
    seen:  turn numbers of every row we have noticed (to detect gaps)
    Returns how many new messages were found.
    """
    new_messages = 0
    for turn in page.evaluate(COLLECT_JS):
        if turn["turn"] >= 0:
            seen.add(turn["turn"])
        key = turn["id"] or f"turn-{turn['turn']}-{turn['role']}"
        if not turn["text"]:
            continue
        if key not in found:
            new_messages += 1
        found[key] = turn  # newer reading replaces older
    return new_messages


def scroll_to_top(page: Page, scroller, found: dict, seen: set) -> None:
    """Jump to the top repeatedly until nothing new appears there."""
    stable_rounds = 0
    last_signature = None
    for _ in range(MAX_TOP_ATTEMPTS):
        scroller.evaluate("el => { el.scrollTop = 0; }")
        time.sleep(TOP_PAUSE_SECONDS)
        collect_visible(page, found, seen)

        metrics = scroller.evaluate(METRICS_JS)
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
        collect_visible(page, found, seen)

        metrics = scroller.evaluate(METRICS_JS)
        if metrics["top"] + metrics["height"] >= metrics["total"] - 2:
            time.sleep(1.0)  # if the page grows, we were not really at the end
            collect_visible(page, found, seen)
            again = scroller.evaluate(METRICS_JS)
            if again["total"] == metrics["total"]:
                return
            continue

        if step_number % 20 == 0:
            print(f"  scrolling... position {metrics['top']}/{metrics['total']}, "
                  f"messages so far: {len(found)}")

        step = int(metrics["height"] * SCROLL_FRACTION)
        scroller.evaluate(f"el => {{ el.scrollTop += {step}; }}")
        time.sleep(PAUSE_SECONDS)


def find_gaps(seen: set) -> list[int]:
    """Return the turn numbers missing between the first and last seen row."""
    if not seen:
        return []
    return [i for i in range(min(seen), max(seen) + 1) if i not in seen]


def build_chat(title: str, found: dict) -> Chat:
    """Turn the collected messages into a Chat, in the original order."""
    ordered = sorted(found.values(), key=lambda turn: turn["turn"])
    messages = []
    for turn in ordered:
        role = Role.USER if turn["role"] == "user" else Role.ASSISTANT
        messages.append(Message(role, turn["text"]))
    return Chat(title=title, source="chatgpt", messages=messages)


def read_chat(page: Page) -> Chat:
    """Scroll through the open chat and return all of its messages."""
    page.wait_for_selector(MESSAGE_SELECTOR, timeout=15000)
    title = page.title().removesuffix(" - ChatGPT").strip() or "ChatGPT chat"

    found: dict[str, dict] = {}
    seen: set[int] = set()

    if not page.evaluate(MARK_SCROLLER_JS):
        print("Short chat (nothing to scroll): reading what is on screen.")
        time.sleep(1.0)
        collect_visible(page, found, seen)
        return build_chat(title, found)

    scroller = page.locator(SCROLLER)

    for attempt in range(1, MAX_PASSES + 1):
        print(f"Pass {attempt}: going to the top...")
        scroll_to_top(page, scroller, found, seen)
        print(f"  top reached, first turn number: {min(seen) if seen else '?'}")
        scroll_down_pass(page, scroller, found, seen)

        gaps = find_gaps(seen)
        print(f"  pass {attempt} done: turns seen {len(seen)}, "
              f"messages with text {len(found)}, gaps {len(gaps)}")
        if not gaps:
            break  # complete
    else:
        print("Warning: the chat may be incomplete.")
        if gaps:
            print("  missing turn numbers (first 30):", gaps[:30])

    return build_chat(title, found)