"""What an editor can see of `ev.<tag>.<property>`.

An element's style properties are reached through `__getattr__` and
`__setattr__`, checked against a tuple of names. That works perfectly at run
time and is completely invisible to a type checker, so `ev.lbl_0.background`
offered no completion and was reported as an unknown attribute by anything
strict enough to look.

The fix is annotations without values: they tell an editor the attribute exists
and what type it holds, while leaving the runtime path exactly as it was. The
danger is the two lists drifting - a property added to one and not the other -
so the check is that they are the same list, not that some particular name is
present.

No GUI construction here: this reads class declarations, so it runs headless.
"""

import pytest

from iterlab.layout.schema import UNIVERSAL_STYLE, style_fields_for


@pytest.fixture
def handles():
    from iterlab.ui import elements

    return elements


def test_every_style_property_is_declared(handles):
    """The list an editor reads must match the list the code honours."""
    declared = set(handles._TextHandle.__annotations__)
    assert declared == set(handles.STYLE_PROPERTY_NAMES)


def test_the_axes_declares_what_it_honours(handles):
    """A plot has one style property, and it is spelled the same way."""
    assert set(handles.AxesHandle.__annotations__) >= set(UNIVERSAL_STYLE)
    assert handles.AxesHandle.STYLE_PROPERTIES == UNIVERSAL_STYLE


def test_the_declarations_match_the_schema(handles):
    """`ev` and the properties panel have to agree on what exists."""
    assert set(handles.STYLE_PROPERTY_NAMES) == set(style_fields_for("button"))


def test_declaring_them_did_not_create_class_attributes(handles):
    """Annotations only.

    A value here would put a plain class attribute in front of the descriptor
    protocol, and `ev.lbl_0.background = "red"` would set an ordinary attribute
    instead of restyling the live widget - the feature would still type-check
    and silently stop working.
    """
    for name in handles.STYLE_PROPERTY_NAMES:
        assert not hasattr(handles._TextHandle, name), name
        assert not hasattr(handles.LabelHandle, name), name


def test_the_text_property_is_visible_to_an_editor(handles):
    """`.text` is a real property, so it needs no help - state that it is one."""
    assert isinstance(handles._CaptionHandle.text, property)
    assert isinstance(handles._BoxHandle.text, property)


def test_the_number_box_value_is_too(handles):
    assert isinstance(handles.NumberBoxHandle.value, property)


def test_a_selector_path_is_too(handles):
    assert isinstance(handles._SelectHandle.path, property)


def test_an_axes_is_a_matplotlib_axes(handles):
    """Why a stub can promise matplotlib's own signatures for `ev.ax_0.plot`."""
    from matplotlib.axes import Axes

    assert issubclass(handles.AxesHandle, Axes)


def test_the_package_is_marked_as_typed():
    """PEP 561. Without this file a checker ignores our annotations entirely."""
    from pathlib import Path

    import iterlab

    marker = Path(iterlab.__file__).parent / "py.typed"
    assert marker.exists(), "py.typed must sit beside the package"
