"""Builds a clean HTML page from a Chat object.

The same HTML is used as the base for the PDF export. Keeping this in
one place means the PDF always looks the same, no matter which AI
service the chat came from.
"""

import base64  # turns binary files (fonts) into plain text
from html import escape  # turns special characters like < and & into safe text
from pathlib import Path  # cross-platform file paths

from chat_exporter.models import Chat, ChatLanguage, Role  # shared structures

# Folder that contains the font files (…/chat_exporter/assets/fonts).
# __file__ is the path of this python file; .parent.parent goes up two
# levels (exporters -> chat_exporter), then we step into assets/fonts.
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def font_face_css(file_name: str, weight: int) -> str:
    """Return a CSS @font-face rule with the font embedded inside it."""
    font_bytes = (FONTS_DIR / file_name).read_bytes()  # read the raw file
    encoded = base64.b64encode(font_bytes).decode("ascii")  # bytes -> text
    return (
        "@font-face {"
        " font-family: 'Vazirmatn';"
        f" font-weight: {weight};"
        f" src: url(data:font/ttf;base64,{encoded}) format('truetype');"
        " }"
    )

def role_label(role: Role) -> str:
    """Return the human-readable name shown above each message."""
    if role == Role.USER:
        return "You"
    return "AI"


def text_direction(language: ChatLanguage) -> str:
    """Return the value of the HTML 'dir' attribute for a language."""
    if language == ChatLanguage.PERSIAN:
        return "rtl"   # right-to-left
    if language == ChatLanguage.MIXED:
        return "auto"  # the browser decides per paragraph
    return "ltr"       # English: left-to-right


def build_html(chat: Chat, language: ChatLanguage = ChatLanguage.ENGLISH) -> str:
    """Convert a Chat into a complete HTML document (as a string)."""
    direction = text_direction(language)

    # Embed both font weights directly into the page.
    fonts_css = (
        font_face_css("Vazirmatn-Regular.ttf", 400)
        + font_face_css("Vazirmatn-Bold.ttf", 700)
    )

    # The small "You" / "AI" label is English, so it only flips to the
    # right side when the whole chat is Persian.
    label_direction = "rtl" if language == ChatLanguage.PERSIAN else "ltr"

    parts = []  # we collect pieces of HTML here, then join them at the end

    for message in chat.messages:
        # A blank line separates paragraphs. We wrap each paragraph in its
        # own <p> tag so each one can have its own text direction.
        paragraphs = [
            f'<p dir="{direction}">{escape(paragraph)}</p>'
            for paragraph in message.text.split("\n\n")
            if paragraph.strip()  # skip paragraphs that are empty
        ]

        parts.append(
            f'<div class="message {message.role.value}">'
            f'<div class="label" dir="{label_direction}">'
            f"{role_label(message.role)}</div>"
            f'{"".join(paragraphs)}'
            f"</div>"
        )

    body = "\n".join(parts)

    return f"""<!DOCTYPE html>
<html lang="{language.value if language != ChatLanguage.MIXED else 'en'}">
<head>
<meta charset="utf-8">
<title>{escape(chat.title)}</title>
<style>
    {fonts_css}
  body {{ font-family: 'Vazirmatn', sans-serif; max-width: 800px; margin: 2rem auto; }}
  h1 {{ font-size: 1.5rem; }}
  .message {{ margin: 1rem 0; padding: 0.75rem 1rem; border-radius: 8px; }}
  .user {{ background: #eef3fb; }}
  .assistant {{ background: #f5f5f5; }}
  .label {{ font-weight: bold; margin-bottom: 0.25rem; }}
  p {{ margin: 0.5rem 0; white-space: pre-wrap; }}
</style>
</head>
<body>
<h1 dir="{direction if direction != 'auto' else 'auto'}">{escape(chat.title)}</h1>
{body}
</body>
</html>
"""