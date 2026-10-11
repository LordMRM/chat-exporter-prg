"""The graphical window of chat-exporter-prg (built with Tkinter).

Part 1: layout and choices only. The Export button is connected to the
real export job in the next step.
"""
import queue  # a thread-safe mailbox between the worker and the window
import threading  # runs the export in the background
from pathlib import Path
import tkinter as tk  # the window toolkit that ships with Python
from tkinter import ttk  # "themed" widgets: nicer-looking buttons, menus...
from chat_exporter.paths import APP_FOLDER_NAME, get_output_dir, open_folder

from chat_exporter.models import ChatLanguage
from chat_exporter.paths import APP_FOLDER_NAME
from chat_exporter.pipeline import run_export
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

        # The worker thread puts ("status", text), ("continue", None),
        # ("done", path) or ("error", text) here; the window reads them.
        self.messages: queue.Queue = queue.Queue()
        # Set by the Continue button, waited on by the worker thread.
        self.continue_event = threading.Event()
        self.is_running = False

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

        # Hidden until the program needs the user to log in / open a chat.
        self.continue_button = ttk.Button(
            frame, text="Continue (the chat is open)",
            command=self._on_continue_clicked,
        )

        # Shown only after a successful export.
        self.open_button = ttk.Button(
            frame, text="Open the folder",
            command=lambda: open_folder(get_output_dir()),
        )

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
        """Start the export in a background thread."""
        if self.is_running:
            return
        self.is_running = True
        self.export_button.state(["disabled"])
        self.continue_event.clear()
        self.open_button.pack_forget()

        settings = self.get_settings()
        worker = threading.Thread(
            target=self._worker, args=(settings,), daemon=True
        )
        worker.start()
        self.after(100, self._poll_messages)  # start checking the mailbox

    def _on_continue_clicked(self) -> None:
        """The user says the chat is open: let the worker go on."""
        self.continue_button.pack_forget()
        self.continue_event.set()

    def _worker(self, settings: Settings) -> None:
        """Runs in the background thread. Never touches widgets directly."""

        def progress(text: str) -> None:
            self.messages.put(("status", text))

        def wait_for_user() -> None:
            self.messages.put(("continue", None))  # ask the window to show the button
            self.continue_event.wait()  # sleep until the button is clicked

        try:
            path = run_export(settings, progress, wait_for_user)
            self.messages.put(("done", str(path)))
        except Exception as error:  # show any problem to the user
            self.messages.put(("error", str(error) or type(error).__name__))

    def _poll_messages(self) -> None:
        """Runs in the window's own thread: show what the worker reported."""
        finished = False
        while True:
            try:
                kind, value = self.messages.get_nowait()
            except queue.Empty:
                break

            if kind == "status":
                self.status_var.set(value)
            elif kind == "continue":
                self.continue_button.pack(fill="x", ipady=6, pady=(8, 0))
            elif kind == "done":
                self.status_var.set(f"Done! Saved to:\n{value}")
                self.open_button.pack(fill="x", ipady=6, pady=(8, 0))
                finished = True
            elif kind == "error":
                self.status_var.set(f"Error: {value}")
                finished = True

        if finished:
            self.is_running = False
            self.export_button.state(["!disabled"])
            self.continue_button.pack_forget()
        else:
            self.after(100, self._poll_messages)  # check again soon

def run_gui() -> None:
    """Create the window and keep it open until the user closes it."""
    App().mainloop()