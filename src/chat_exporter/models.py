"""Shared data structures used by every part of chat-exporter-prg.

Adapters (which read chats from websites) produce these objects and
exporters (which write PDF/DOCX files) consume them. Because both sides
only know about these classes, they never depend on each other.
"""

from dataclasses import dataclass, field  # tools for creating simple data classes
from enum import Enum                     # tool for defining a fixed set of choices


class Role(Enum):
    """Who wrote a message."""

    USER = "user"            # the human
    ASSISTANT = "assistant"  # the AI

class ChatLanguage(Enum):
    """The language of a chat. This decides the text direction of the output."""

    ENGLISH = "en"  # left-to-right
    PERSIAN = "fa"  # right-to-left
    MIXED = "mixed"  # both languages: each paragraph picks its own direction

@dataclass
class Message:
    """A single message inside a chat."""

    role: Role  # who wrote it (see Role above)
    text: str   # the message content, as plain text


@dataclass
class Chat:
    """A whole conversation: a title, the source AI, and a list of messages."""

    title: str                   # the chat title shown on the website
    source: str                  # which AI service it came from, e.g. "claude"
    messages: list[Message] = field(default_factory=list)  # starts empty
    
TABLE_MARKER = "[[TABLE]]"  # first line of a text block that holds a table


def parse_table(block: str) -> list[list[str]] | None:
    """If the text block is a table, return its rows; otherwise None."""
    if not block.startswith(TABLE_MARKER):
        return None
    lines = block.split("\n")[1:]  # drop the marker line
    return [line.split("\t") for line in lines if line.strip()]