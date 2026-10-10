"""The choices a user makes in the program, collected in one place.

The window (GUI) fills a Settings object and hands it to the pipeline.
Using Enums means a choice can only be one of the allowed values.
"""

from dataclasses import dataclass  # simple data classes
from enum import Enum  # fixed sets of choices

from chat_exporter.models import ChatLanguage  # English / Persian / mixed


class Service(Enum):
    """Which AI website the chat comes from."""

    CLAUDE = "claude"
    GEMINI = "gemini"
    CHATGPT = "chatgpt"


class BrowserChoice(Enum):
    """Which browser the user wants to use."""

    CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"


class OutputFormat(Enum):
    """Which file type to create. The value doubles as the file extension."""

    PDF = "pdf"
    DOCX = "docx"


@dataclass
class Settings:
    """Everything the user can choose. Defaults are used if nothing is set."""

    service: Service = Service.CLAUDE
    browser: BrowserChoice = BrowserChoice.CHROME
    output_format: OutputFormat = OutputFormat.PDF
    language: ChatLanguage = ChatLanguage.MIXED