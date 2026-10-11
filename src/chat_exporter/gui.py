"""The graphical window of chat-exporter-prg (built with Tkinter).

Part 1: layout and choices only. The Export button is connected to the
real export job in the next step.
"""

import tkinter as tk  # the window toolkit that ships with Python
from tkinter import ttk  # "themed" widgets: nicer-looking buttons, menus...

from chat_exporter.models import ChatLanguage
from chat_exporter.paths import APP_FOLDER_NAME
from chat_exporter.settings import (
    BrowserChoice,
    OutputFormat,
    Service,
    Settings,
)

PRIVACY_TEXT = (
    "Everything runs locally on your computer.\n"
    "No data is collected, stored by us, or sent anywhere."
)

# Texts shown under the browser choice. Chrome and Edge open a separate
# window that only this program uses, so the user logs in there once.
BROWSER_HINTS = {
    BrowserChoice.CHROME: (
        "Opens a separate Chrome window for this program.\n"
        "Log in to your AI service there once; it will be remembered."
    ),
    BrowserChoice.EDGE: (
        "Opens a separate Edge window for this program.\n"
        "Log in to your AI service there once; it will be remembered."
    ),
    BrowserChoice.FIREFOX: (
        "Opens a Firefox window for this program (not ready yet).\n"
        "Your login stays inside Firefox on this computer only."
    ),
}

# Labels shown to the user for each language option.
LANGUAGE_LABELS = {
    ChatLanguage.ENGLISH: "English",
    ChatLanguage.PERSIAN: "Persian",
    ChatLanguage.MIXED: "Both (mixed)",
}

# Colors of the window. Change a value here to restyle the whole program.
BACKGROUND = "#1a1a2e"   # dark blue-violet
TEXT_COLOR = "#ccff00"   # phosphor yellow
HINT_COLOR = "#ffe600"   # slightly dimmer yellow, for secondary texts
BUTTON_BG = "#2b2b4a"    # button background (a bit lighter than the window)
BUTTON_ACTIVE = "#3a3a66"  # button color while the mouse is over it

class App(tk.Tk):
    """The main window. Inherits from tk.Tk, which is the window itself."""

    def __init__(self) -> None:
        super().__init__()  # create the actual window first
        self.title("Chat Exporter")
        self.geometry("520x640")
        self.resizable(False, False)

        self.configure(bg=BACKGROUND)  # color of the window itself
        self._apply_theme()

        # Tkinter "variables" hold the current value of each choice.
        # Widgets update them automatically when the user clicks.
        self.service_var = tk.StringVar(value=Service.CLAUDE.value)
        self.browser_var = tk.StringVar(value=BrowserChoice.CHROME.value)
        self.format_var = tk.StringVar(value=OutputFormat.PDF.value)
        self.language_var = tk.StringVar(value=ChatLanguage.MIXED.value)
        self.hint_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")

        self._build_widgets()
        self._update_browser_hint()

    # ---------- building the layout ----------

    def _apply_theme(self) -> None:
        """Set colors for all ttk widgets."""
        style = ttk.Style(self)
        style.theme_use("clam")  # this theme respects custom colors

        style.configure(".", background=BACKGROUND, foreground=TEXT_COLOR)
        style.configure("TFrame", background=BACKGROUND)
        style.configure("TLabel", background=BACKGROUND, foreground=TEXT_COLOR)
        style.configure("Hint.TLabel", foreground=HINT_COLOR)
        style.configure(
            "TLabelframe", background=BACKGROUND, bordercolor=HINT_COLOR
        )
        style.configure(
            "TLabelframe.Label", background=BACKGROUND, foreground=TEXT_COLOR
        )
        style.configure(
            "TRadiobutton", background=BACKGROUND, foreground=TEXT_COLOR
        )
        style.map("TRadiobutton", background=[("active", BACKGROUND)])
        style.configure(
            "TButton",
            background=BUTTON_BG,
            foreground=TEXT_COLOR,
            bordercolor=TEXT_COLOR,
            padding=6,
        )
        style.map("TButton", background=[("active", BUTTON_ACTIVE)])

    def _build_widgets(self) -> None:
        """Create and place all the widgets."""
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        # Privacy notice
        ttk.Label(
            frame, text=PRIVACY_TEXT, justify="center"
        ).pack(pady=(0, 12))

        # Each choice group is built by the same helper function.
        self._radio_group(
            frame, "1. AI service", self.service_var,
            [(s.name.title() if s != Service.CHATGPT else "ChatGPT", s.value)
             for s in Service],
        )

        self._radio_group(
            frame, "2. Browser", self.browser_var,
            [(b.name.title(), b.value) for b in BrowserChoice],
            command=self._update_browser_hint,
        )
        ttk.Label(
            frame, textvariable=self.hint_var, justify="left",
            style="Hint.TLabel", wraplength=470,
        ).pack(anchor="w", pady=(0, 8))

        self._radio_group(
            frame, "3. File type", self.format_var,
            [("PDF", OutputFormat.PDF.value), ("Word (DOCX)", OutputFormat.DOCX.value)],
        )

        self._radio_group(
            frame, "4. Language of the chat", self.language_var,
            [(LANGUAGE_LABELS[lang], lang.value) for lang in ChatLanguage],
        )

        ttk.Label(
            frame,
            text=f"Files are saved in:  Documents / {APP_FOLDER_NAME}",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(8, 12))

        self.export_button = ttk.Button(
            frame, text="Export chat", command=self._on_export_clicked
        )
        self.export_button.pack(fill="x", ipady=6)

        ttk.Label(
            frame, textvariable=self.status_var, wraplength=470, justify="left"
        ).pack(anchor="w", pady=(12, 0))

    def _radio_group(self, parent, title, variable, options, command=None) -> None:
        """Build a titled box with one radio button per option.

        options is a list of (label_to_show, value_to_store) pairs.
        """
        box = ttk.LabelFrame(parent, text=title, padding=8)
        box.pack(fill="x", pady=4)
        for label, value in options:
            ttk.Radiobutton(
                box, text=label, value=value, variable=variable, command=command
            ).pack(side="left", padx=(0, 16))

    # ---------- reacting to the user ----------

    def _update_browser_hint(self) -> None:
        """Show the explanation that matches the selected browser."""
        self.hint_var.set(BROWSER_HINTS[BrowserChoice(self.browser_var.get())])

    def get_settings(self) -> Settings:
        """Turn the current widget values into a Settings object."""
        return Settings(
            service=Service(self.service_var.get()),
            browser=BrowserChoice(self.browser_var.get()),
            output_format=OutputFormat(self.format_var.get()),
            language=ChatLanguage(self.language_var.get()),
        )

    def _on_export_clicked(self) -> None:
        """Temporary: just show the chosen settings (real export comes next)."""
        self.status_var.set(f"Chosen: {self.get_settings()}")


def run_gui() -> None:
    """Create the window and keep it open until the user closes it."""
    App().mainloop()