"""Small helpers shared by the display-dependent tests."""
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
