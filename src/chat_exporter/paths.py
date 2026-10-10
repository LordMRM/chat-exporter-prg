"""Decides where exported files are saved and what they are called.

Everything is saved in one fixed folder: <Documents>/AI-Chat-Exports.
The Documents folder is found with platformdirs, so it works the same
way on Linux, Windows and macOS.
"""

import re  # regular expressions: pattern matching inside text
from pathlib import Path  # cross-platform file paths

from platformdirs import user_documents_dir  # finds the user's Documents folder

APP_FOLDER_NAME = "AI-Chat-Exports"  # name of our folder inside Documents
MAX_NAME_LENGTH = 80  # long file names cause problems on some systems

# Characters that are not allowed in file names on Windows (the strictest
# system), plus invisible control characters (codes 0 to 31).
FORBIDDEN_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Names that Windows reserves for old hardware devices. A file called
# "CON.pdf" cannot be created there, so we avoid these names everywhere.
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def get_output_dir() -> Path:
    """Return the output folder, creating it first if it does not exist."""
    folder = Path(user_documents_dir()) / APP_FOLDER_NAME
    # parents=True: also create missing parent folders.
    # exist_ok=True: do not raise an error if the folder already exists.
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def safe_file_stem(title: str) -> str:
    """Turn a chat title into a safe file name (without the extension)."""
    # Replace every forbidden character with an underscore.
    name = FORBIDDEN_CHARACTERS.sub("_", title)

    # Collapse repeated spaces and line breaks into single spaces.
    name = " ".join(name.split())

    # Cut to the maximum length. Windows also dislikes names that end in
    # a dot or a space, so we strip those from both ends.
    name = name[:MAX_NAME_LENGTH].strip(" .")

    if not name:  # the title was empty or contained only bad characters
        name = "chat"

    if name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"_{name}"  # e.g. "CON" becomes "_CON"

    return name


def unique_path(folder: Path, stem: str, extension: str) -> Path:
    """Return a path that does not exist yet, adding (2), (3)... if needed."""
    candidate = folder / f"{stem}.{extension}"
    counter = 2
    while candidate.exists():  # keep trying until we find a free name
        candidate = folder / f"{stem} ({counter}).{extension}"
        counter += 1
    return candidate


def build_output_path(title: str, extension: str) -> Path:
    """Return the full path for a new export, e.g. build_output_path("Hi", "pdf")."""
    return unique_path(get_output_dir(), safe_file_stem(title), extension)