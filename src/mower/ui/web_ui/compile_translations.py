"""Script to compile translations for the web interface.

This script compiles the .po translation files into .mo
files that can be used by Flask-Babel.
Run this script after updating the translation files.
"""

import subprocess
from pathlib import Path


def compile_translations():
    """Compile all translation files."""
    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Path to the translations directory
    translations_dir = script_dir / "translations"

    # Check if the translations directory exists
    if not translations_dir.exists():
        print(f"Translations directory not found: {translations_dir}")
        return

    # Compile all .po files to .mo files
    for lang_dir in translations_dir.iterdir():
        if lang_dir.is_dir():
            lc_messages_dir = lang_dir / "LC_MESSAGES"
            if lc_messages_dir.exists():
                po_file = lc_messages_dir / "messages.po"
                if po_file.exists():
                    mo_file = lc_messages_dir / "messages.mo"
                    try:
                        # Use pybabel to compile the .po file to .mo
                        subprocess.run(
                            [
                                "pybabel",
                                "compile",
                                "-f",
                                "-i",
                                str(po_file),
                                "-o",
                                str(mo_file),
                            ],
                            check=True,
                        )
                        print(f"Compiled {po_file} to {mo_file}")
                    except subprocess.CalledProcessError as e:
                        print(f"Error compiling {po_file}: {e}")
                    except FileNotFoundError:
                        print(
                            "pybabel command not found. "
                            "Make sure Flask-Babel is installed."
                        )
                else:
                    print(f"No messages.po file found in {lc_messages_dir}")
            else:
                print(f"No LC_MESSAGES directory found in {lang_dir}")

    print("Translation compilation complete.")


if __name__ == "__main__":
    compile_translations()
