"""Small helpers shared by the display-dependent tests."""

import tkinter

#: X11 wants keysym *names*, where Windows Tk accepts the bare character. "." is
#: "period" there, so a test typing a filename passed on Windows and failed on
#: Linux with `unknown keysym "."`. Only CI ever saw it, which is the whole
#: reason CI runs the display-dependent suite on Linux at all.
KEYSYMS = {
    ".": "period", ",": "comma", "-": "minus", "_": "underscore",
    " ": "space", "/": "slash", "\\": "backslash", ":": "colon",
    ";": "semicolon", "(": "parenleft", ")": "parenright", "*": "asterisk",
    "+": "plus", "=": "equal", "%": "percent", "#": "numbersign",
}


def keysym_for(character):
    """The name Tk knows this character by, on every platform."""
    return KEYSYMS.get(character, character)


def press_key(widget, character):
    """Deliver a KeyRelease for `character`, whatever keyboard is installed.

    `event_generate(keysym=...)` asks Tk to find the keycode that would produce
    that symbol on the *current* layout, and a machine set to a non-Latin
    keyboard has none - it raises `no keycode for keysym "x"` and the suite
    fails for a reason that has nothing to do with iterlab. Falling back to the
    `<KeyRelease-x>` form still delivers the event; it arrives carrying no
    keysym, which is fine for every test that only needs the keystroke itself.

    Returns whether the keysym survived, so the one test that reads the payload
    can say it cannot run here rather than assert against "??".
    """
    try:
        widget.event_generate("<KeyRelease>", keysym=keysym_for(character), when="now")
        return True
    except tkinter.TclError:
        widget.event_generate(f"<KeyRelease-{character}>", when="now")
        return False
