"""Reads a conversation from the Gemini website (gemini.google.com).

Gemini uses custom HTML tags instead of data-testid:
  <user-query>      -> a message written by the person
  <model-response>  -> a reply written by Gemini
Replies contain source citations (footnotes, source chips) that we
remove before reading, so only the real text is exported.

Part 1: short chats only (no scrolling yet).
"""

from playwright.sync_api import Page

from chat_exporter.models import Chat, Message, Role

TURN_SELECTOR = "user-query, model-response"

# JavaScript that runs inside the page and returns plain data.
COLLECT_JS = """
() => {
  // Things that must never appear in the exported text.
  const REMOVE = [
    'source-footnote', 'sup.superscript', 'sources-carousel-inline',
    'source-inline-chip', 'sources-list', 'thinking-overlay',
    '.cdk-visually-hidden', 'mat-icon', 'gem-icon', 'button',
  ].join(', ');

  // Copy a node, delete the unwanted parts from the COPY (the real page
  // stays untouched), and return the copy.
  const clean = (node) => {
    const copy = node.cloneNode(true);
    copy.querySelectorAll(REMOVE).forEach((e) => e.remove());
    return copy;
  };

  // Plain text with all whitespace collapsed to single spaces.
  const textOf = (node) =>
    clean(node).textContent.replace(/\\s+/g, ' ').trim();

  // Walk the children in page order and turn them into text blocks.
  const blocksOf = (root) => {
    const out = [];
    const walk = (element) => {
      for (const child of element.children) {
        const tag = child.tagName.toLowerCase();
        // Skip screen-reader-only elements (e.g. the hidden "You said" heading).
        if (child.matches('.cdk-visually-hidden')) continue;
        if (tag === 'p' || /^h[1-6]$/.test(tag)) {
          const text = textOf(child);
          if (text) out.push(text);
        } else if (tag === 'ul' || tag === 'ol') {
          let number = 0;
          for (const item of child.children) {
            if (item.tagName.toLowerCase() !== 'li') continue;
            number += 1;
            const text = textOf(item);
            if (text) out.push((tag === 'ol' ? number + '. ' : '\\u2022 ') + text);
          }
        } else if (tag === 'pre') {
          // Code keeps its line breaks and spaces exactly as they are.
          const code = clean(child).textContent.replace(/\\s+$/, '');
          if (code) out.push(code);
        } else if (tag === 'table') {
          // Marker line + one line per row, cells separated by a tab.
          const lines = ['[[TABLE]]'];
          for (const row of child.querySelectorAll('tr')) {
            const cells = [...row.children].map((cell) => textOf(cell));
            lines.push(cells.join('\\t'));
          }
          out.push(lines.join('\\n'));
        } else {
          walk(child);  // a wrapper element: look inside it
        }
      }
    };
    walk(root);
    return out;
  };

  const turns = [];
  for (const turn of document.querySelectorAll('user-query, model-response')) {
    const isUser = turn.tagName.toLowerCase() === 'user-query';
    // For replies, read only the main text area (not buttons or footers).
    const root = isUser
      ? turn.querySelector('.query-text') || turn
      : turn.querySelector('message-content') || turn;
    turns.push({
      role: isUser ? 'human' : 'assistant',
      text: blocksOf(root).join('\\n\\n'),
    });
  }
  return turns;
}
"""


def read_chat(page: Page) -> Chat:
    """Read the Gemini chat that is currently open in the given page."""
    page.wait_for_selector(TURN_SELECTOR, timeout=15000)

    # Tab titles look like "Chat title - Google Gemini" (we will check
    # the real format in the test). Fall back to a generic name.
    title = page.title()
    for suffix in (" - Google Gemini", " | Gemini", "Google Gemini"):
        title = title.removesuffix(suffix)
    title = title.strip() or "Gemini chat"

    messages = []
    for turn in page.evaluate(COLLECT_JS):
        if not turn["text"]:
            continue  # skip turns without readable text
        role = Role.USER if turn["role"] == "human" else Role.ASSISTANT
        messages.append(Message(role, turn["text"]))

    return Chat(title=title, source="gemini", messages=messages)