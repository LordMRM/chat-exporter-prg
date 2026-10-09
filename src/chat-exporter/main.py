"""Entry point of chat-exporter-prg (temporary environment check)."""

import platform  # standard library: info about the OS and Python
import sys       # standard library: info about the running interpreter

import docx          # python-docx: proves the package is installed
import platformdirs  # proves the package is installed
import playwright    # proves the package is installed


def main() -> None:
    """Print basic information to confirm the environment works."""
    print("Environment check OK")
    print(f"Operating system: {platform.system()}")
    print(f"Python version:   {sys.version.split()[0]}")
    print(f"Running from:     {sys.executable}")


# This block runs only when the file is executed directly,
# not when another file imports it.
if __name__ == "__main__":
    main()