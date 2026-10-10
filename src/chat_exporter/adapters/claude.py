"""Reads a conversation from the claude.ai website.

claude.ai marks every message with a data-testid attribute:
  user-message       -> a message written by the person
  assistant-message  -> a reply written by Claude
Inside those blocks, the real text lives in ordinary tags (p, li, pre,
headings). Everything else (status bars, buttons) is ignored.
"""

from playwright.sync_api import Page

from chat_exporter.models import Chat, Message, Role

# CSS selector that matches both kinds of message, in page order.
MESSAGE_SELECTOR = (
    '[data-testid="user-message"], [data-testid="assistant-message"]'
)

# Tags whose text we keep. Nested ones (like <li> inside <ul>) are fine:
# we only read the innermost text tags listed here.
TEXT_SELECTOR = "p, li, pre, h1, h2, h3, h4, h5, h6"


def read_message_text(message_element) -> str:
    """Return the readable text of one message, paragraphs separated by blank lines."""
    blocks = []
    for element in message_element.query_selector_all(TEXT_SELECTOR):
        # Skip screen-reader-only headings such as "Claude responded: ...".
        classes = element.get_attribute("class") or ""
        if "sr-only" in classes:
            continue

        text = element.inner_text().strip()
        if text:
            blocks.append(text)
    return "\n\n".join(blocks)


def read_chat(page: Page) -> Chat:
    """Read the chat that is currently open in the given page."""
    # The tab title looks like "My chat title - Claude"; remove the suffix.
    title = page.title().removesuffix(" - Claude").strip() or "Claude chat"

    messages = []
    for element in page.query_selector_all(MESSAGE_SELECTOR):
        testid = element.get_attribute("data-testid")
        role = Role.USER if testid == "user-message" else Role.ASSISTANT
        text = read_message_text(element)
        if text:
            messages.append(Message(role, text))

    return Chat(title=title, source="claude", messages=messages)