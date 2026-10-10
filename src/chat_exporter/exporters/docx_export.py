"""Turns a Chat into a Word (.docx) file using python-docx.

Unlike the PDF export, Word files are not built from HTML. We create
the document piece by piece: a title, then for each message a bold
label ("You" / "AI") followed by its paragraphs.

Word does not detect text direction by itself, so for Persian we set
right-to-left direction, right alignment and the complex-script font
explicitly on every paragraph.
"""
import unicodedata  # standard library: knows the direction of every character
from pathlib import Path  # cross-platform file paths

from docx import Document  # python-docx: creates and edits Word documents
from docx.enum.text import WD_ALIGN_PARAGRAPH  # left / right / center alignment
from docx.oxml import OxmlElement  # lets us create raw XML elements
from docx.oxml.ns import qn  # builds proper XML names like "w:bidi"

from chat_exporter.exporters.html_builder import role_label  # reuse "You" / "AI"
from chat_exporter.models import Chat, ChatLanguage  # our shared structures

FONT_NAME = "Vazirmatn"  # must be installed on the computer that opens the file

def starts_rtl(text: str) -> bool:
    """Return True if the first strongly-directional letter is right-to-left.

    This is the same rule browsers use for dir="auto": spaces, digits and
    punctuation have no direction, so we skip them until we meet a real letter.
    """
    for character in text:
        kind = unicodedata.bidirectional(character)
        if kind in ("R", "AL"):  # Hebrew / Arabic / Persian letters
            return True
        if kind == "L":          # Latin (and other left-to-right) letters
            return False
    return False  # no letters at all (e.g. only numbers): default to LTR


def is_rtl(text: str, language: ChatLanguage) -> bool:
    """Decide the direction of one paragraph for the chosen chat language."""
    if language == ChatLanguage.PERSIAN:
        return True               # always right-to-left
    if language == ChatLanguage.MIXED:
        return starts_rtl(text)   # decide paragraph by paragraph
    return False                  # English: always left-to-right

def set_run_font(run, rtl: bool) -> None:
    """Apply the font to a piece of text. For Persian also set the
    complex-script font and mark the run as right-to-left."""
    run.font.name = FONT_NAME  # font for Latin letters

    # run._element is the raw XML of this run; rPr holds its properties.
    properties = run._element.get_or_add_rPr()

    # rFonts holds the font names for each kind of script.
    fonts = properties.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.append(fonts)
    fonts.set(qn("w:cs"), FONT_NAME)  # "cs" = complex script (Persian, Arabic)

    if rtl:
        properties.append(OxmlElement("w:rtl"))  # this text is right-to-left


def set_paragraph_direction(paragraph, rtl: bool) -> None:
    """Set the paragraph direction and alignment."""
    if rtl:
        # "bidi" = bidirectional paragraph, i.e. right-to-left layout.
        # In a bidi paragraph Word already starts text on the right side.
        # We must NOT set alignment to RIGHT here: Word flips left/right
        # inside bidi paragraphs, so RIGHT would push the text to the left.
        paragraph._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT


def add_text(document, text: str, rtl: bool, bold: bool = False) -> None:
    """Add one paragraph with the right direction, alignment and font."""
    paragraph = document.add_paragraph()
    set_paragraph_direction(paragraph, rtl)
    run = paragraph.add_run(text)
    run.bold = bold
    set_run_font(run, rtl)


def export_docx(
    chat: Chat,
    output_path: Path,
    language: ChatLanguage = ChatLanguage.ENGLISH,
) -> Path:
    """Write the chat to a .docx file and return the path of that file."""
    document = Document()  # a new, empty Word document

    # Chat title: its direction follows its own text.
    add_text(document, chat.title, is_rtl(chat.title, language), bold=True)

    for message in chat.messages:
        # Label line: "You" or "AI" in bold. In mixed mode it is English,
        # so it stays left-to-right; in Persian mode everything is RTL.
        label = role_label(message.role)
        add_text(document, label, is_rtl(label, language), bold=True)

        # One Word paragraph for every blank-line-separated block of text.
        for block in message.text.split("\n\n"):
            if block.strip():  # skip empty blocks
                text = block.strip()
                add_text(document, text, is_rtl(text, language))

    document.save(str(output_path))  # write the file to disk
    return output_path