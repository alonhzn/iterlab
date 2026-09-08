"""The session environment handed to every handler.

Owned by the runtime and **never** defined in the researcher's module. That
ownership is the whole mechanism behind Principle IV: reloading a module rebinds
its globals, so anything the researcher's module owned would be destroyed on
every edit — including the data the paradigm promises to keep (research.md R1).

No GUI imports.
"""

from __future__ import annotations


class Ev:
    """Whatever the researcher puts here, plus one attribute per element.

    Attribute names beginning with an underscore are reserved for iterlab, which
    is why element names may not start with one (schema.validate_name).
    """

    def __init__(self):
        # Bypass __setattr__ so the reserved-prefix check does not fire on our
        # own bookkeeping.
        object.__setattr__(self, "_element_names", set())

    # -- element handles -------------------------------------------------

    def _bind_element(self, name: str, handle) -> None:
        """Attach an element handle under the name shown in the designer."""
        object.__setattr__(self, name, handle)
        self._element_names.add(name)

    def _element_handles(self) -> dict:
        return {n: getattr(self, n) for n in sorted(self._element_names)}

    # -- researcher state ------------------------------------------------

    def __setattr__(self, name, value):
        if name.startswith("_"):
            raise AttributeError(
                f"{name!r} is reserved for iterlab. Use a name without a leading underscore."
            )
        object.__setattr__(self, name, value)

    def __repr__(self):
        mine = sorted(self._element_names)
        theirs = sorted(
            k for k in vars(self) if not k.startswith("_") and k not in self._element_names
        )
        return f"<Ev elements={mine} data={theirs}>"
