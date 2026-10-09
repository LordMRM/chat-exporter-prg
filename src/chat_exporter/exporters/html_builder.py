"""Builds a clean HTML page from a Chat object.

The same HTML is used as the base for the PDF export. Keeping this in
one place means the PDF always looks the same, no matter which AI
service the chat came from.
"""

from html import escape  # turns special characters like < and & into safe text

from chat_exporter.models import Chat, Role  # our shared data structures


def role_label(role: Role) -> str:
    """Return the human-readable name shown above each message."""
    if role == Role.USER:
        return "You"
    return "AI"


def build_html(chat: Chat) -> str:
    """Convert a Chat into a complete HTML document (as a string)."""
    parts = []  # we collect pieces of HTML here, then join them at the end

    for message in chat.messages:
        # escape() makes sure text like "<b>" is shown literally and
        # cannot break (or inject into) the page structure.
        safe_text = escape(message.text)

        # Role.USER.value is "user" and Role.ASSISTANT.value is "assistant";
        # we use it as a CSS class so each side can be styled differently.
        parts.append(
            f'<div class="message {message.role.value}">'
            f'<div class="label">{role_label(message.role)}</div>'
            f'<div class="text">{safe_text}</div>'
            f"</div>"
        )

    body = "\n".join(parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(chat.title)}</title>
<style>
  body {{ font-family: sans-serif; max-width: 800px; margin: 2rem auto; }}
  h1 {{ font-size: 1.5rem; }}
  .message {{ margin: 1rem 0; padding: 0.75rem 1rem; border-radius: 8px; }}
  .user {{ background: #eef3fb; }}
  .assistant {{ background: #f5f5f5; }}
  .label {{ font-weight: bold; margin-bottom: 0.25rem; }}
  .text {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>{escape(chat.title)}</h1>
{body}
</body>
</html>
"""