"""Reads a conversation from chatgpt.com.

Every message is an element with data-message-author-role ("user" or
"assistant") and a unique data-message-id. Inside, text lives in p,
headings, lists and tables; code blocks live in a <pre> inside a code
editor widget (the toolbar above it must be ignored).

Part 1: short chats only (no scrolling yet).
"""

from playwright.sync_api import Page

from chat_exporter.models import Chat, Message, Role

MESSAGE_SELECTOR = "[data-message-author-role]"

# JavaScript that runs inside the page and returns plain data.
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
          // Code keeps its line breaks and spaces exactly as they are.
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
          continue;  // toolbar buttons and icons
        } else {
          walk(child);  // a wrapper element: look inside it
        }
      }
    };
    walk(root);
    return out;
  };

  const seen = new Set();
  const turns = [];
  for (const el of document.querySelectorAll('[data-message-author-role]')) {
    const id = el.getAttribute('data-message-id');
    if (id && seen.has(id)) continue;
    if (id) seen.add(id);
    const role = el.getAttribute('data-message-author-role');
    turns.push({ role, text: blocksOf(el).join('\\n\\n') });
  }
  return turns;
}
"""


def read_chat(page: Page) -> Chat:
    """Read the ChatGPT chat that is currently open in the given page."""
    page.wait_for_selector(MESSAGE_SELECTOR, timeout=15000)

    # Tab titles are just the chat title (or "ChatGPT" for new chats).
    title = page.title().removesuffix(" - ChatGPT").strip() or "ChatGPT chat"

    messages = []
    for turn in page.evaluate(COLLECT_JS):
        if not turn["text"]:
            continue
        role = Role.USER if turn["role"] == "user" else Role.ASSISTANT
        messages.append(Message(role, turn["text"]))

    return Chat(title=title, source="chatgpt", messages=messages)