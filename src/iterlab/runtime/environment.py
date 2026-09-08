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
    is why element names may not start with one (schema.validate_tag).
    """

    def __init__(self):
        # Bypass __setattr__ so the reserved-prefix check does not fire on our
        # own bookkeeping.
        object.__setattr__(self, "_element_tags", set())

    # -- element handles -------------------------------------------------

    def _bind_element(self, tag: str, handle) -> None:
        """Attach an element handle under the tag shown in the designer."""
        object.__setattr__(self, tag, handle)
        self._element_tags.add(tag)

    def _unbind_elements(self, tags=None) -> None:
        """Forget element handles, keeping the researcher's own data.

        Called when the widgets those handles point at are destroyed. Passing
        `None` drops them all; a mode switch does that, because every widget
        goes with the mode that built them.
        """
        targets = self._element_tags if tags is None else set(tags)
        for tag in list(targets):
            self.__dict__.pop(tag, None)
            self._element_tags.discard(tag)

    def _rename_element(self, old: str, new: str) -> None:
        """Follow an element renamed in the editor, so `ev.<new>` finds it."""
        if old not in self._element_tags:
            return
        handle = self.__dict__.pop(old, None)
        self._element_tags.discard(old)
        if handle is not None:
            self._bind_element(new, handle)

    def _element_handles(self) -> dict:
        return {t: getattr(self, t) for t in sorted(self._element_tags)}

    # -- researcher state ------------------------------------------------

    def __setattr__(self, name, value):
        if name.startswith("_"):
            raise AttributeError(
                f"{name!r} is reserved for iterlab. Use a name without a leading underscore."
            )
        object.__setattr__(self, name, value)

    def __repr__(self):
        mine = sorted(self._element_tags)
        theirs = sorted(
            k for k in vars(self) if not k.startswith("_") and k not in self._element_tags
        )
        return f"<Ev elements={mine} data={theirs}>"
