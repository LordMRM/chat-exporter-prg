"""Opens the user's own Chrome or Edge and lets Playwright control it.

We start the browser ourselves with a "remote debugging port" and a
profile folder that belongs only to this program. Then Playwright
connects to that port (the CDP protocol) and can read and control pages.
"""

import os  # environment variables (used to find Windows program folders)
import shutil  # shutil.which() searches the PATH for a program
import socket  # low-level networking (used to find a free port)
import subprocess  # starts other programs, like the browser
import sys  # sys.platform tells us which operating system we are on
import time  # sleeping and measuring time
import urllib.request  # a simple way to ask a local address "are you ready?"
from pathlib import Path  # cross-platform file paths

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from chat_exporter.paths import get_profile_dir  # where our profile lives


def find_executable(browser_name: str) -> Path | None:
    """Return the path of the installed browser, or None if not found.

    browser_name is "chrome" or "edge".
    """
    candidates: list[Path] = []

    if sys.platform.startswith("win"):
        # Windows: browsers live in one of a few standard folders.
        roots = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        relative = {
            "chrome": r"Google\Chrome\Application\chrome.exe",
            "edge": r"Microsoft\Edge\Application\msedge.exe",
        }[browser_name]
        candidates = [Path(root) / relative for root in roots if root]

    elif sys.platform == "darwin":
        # macOS: browsers are inside .app bundles in /Applications.
        path = {
            "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        }[browser_name]
        candidates = [Path(path)]

    else:
        # Linux: look for the usual command names on the PATH.
        names = {
            "chrome": ["google-chrome", "google-chrome-stable",
                       "chromium", "chromium-browser"],
            "edge": ["microsoft-edge", "microsoft-edge-stable"],
        }[browser_name]
        for name in names:
            found = shutil.which(name)  # full path, or None if not installed
            if found:
                candidates.append(Path(found))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_free_port() -> int:
    """Ask the operating system for a network port nobody is using."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))  # port 0 means "pick any free port"
        return sock.getsockname()[1]  # the port the system chose


def wait_until_ready(port: int, timeout: float = 20.0) -> None:
    """Wait until the browser answers on its debugging port."""
    url = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + timeout  # the moment we give up
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return  # it answered, so the browser is ready
        except OSError:
            time.sleep(0.3)  # not ready yet, wait a moment and retry
    raise RuntimeError("The browser did not start in time.")


class BrowserSession:
    """Starts the browser, connects Playwright, and cleans up afterwards.

    Usage:
        with BrowserSession("chrome") as page:
            page.goto("https://example.com")
    """

    def __init__(self, browser_name: str = "chrome") -> None:
        self.browser_name = browser_name
        # These start empty and are filled in by __enter__.
        self._process: subprocess.Popen | None = None
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def __enter__(self) -> Page:
        """Runs at the start of a "with" block. Returns an open page."""
        executable = find_executable(self.browser_name)
        if executable is None:
            raise RuntimeError(
                f"Could not find {self.browser_name} on this computer."
            )

        port = find_free_port()
        profile = get_profile_dir(self.browser_name)

        # Start the browser as a separate program.
        self._process = subprocess.Popen(
            [
                str(executable),
                f"--remote-debugging-port={port}",  # lets Playwright connect
                f"--user-data-dir={profile}",       # our own profile folder
                "--no-first-run",                   # skip the welcome screens
                "--no-default-browser-check",       # skip "make default?" popup
                "about:blank",                      # open an empty tab
            ],
            stdout=subprocess.DEVNULL,  # throw away the browser's console noise
            stderr=subprocess.DEVNULL,
        )

        try:
            wait_until_ready(port)
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}"
            )
            context = self._browser.contexts[0]  # the profile's main context
            # Reuse the empty tab if there is one, otherwise open a new one.
            return context.pages[0] if context.pages else context.new_page()
        except Exception:
            self.close()  # something failed: do not leave a browser running
            raise  # then pass the error on

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Runs at the end of a "with" block, even if an error happened."""
        self.close()

    def close(self) -> None:
        """Disconnect Playwright and shut the browser down."""
        if self._browser is not None:
            try:
                self._browser.close()  # for a connected browser: just disconnect
            except Exception:
                pass  # already gone, nothing to do
            self._browser = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

        if self._process is not None:
            self._process.terminate()  # politely ask the browser to quit
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()  # it refused, so force it
            self._process = None