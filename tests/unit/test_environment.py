"""Ev is owned by the runtime, which is what makes reload lossless."""

import pytest

from iterlab.runtime.environment import Ev


def test_researcher_attributes_persist():
    ev = Ev()
    ev.data = [1, 2, 3]
    ev.model = {"fit": True}
    assert ev.data == [1, 2, 3]
    assert ev.model == {"fit": True}


def test_element_handles_reachable_by_designer_name():
    ev = Ev()
    handle = object()
    ev._bind_element("spectrum", handle)
    assert ev.spectrum is handle


def test_underscore_names_are_reserved():
    ev = Ev()
    with pytest.raises(AttributeError):
        ev._secret = 1


def test_element_handles_listed_separately_from_researcher_state():
    ev = Ev()
    ev._bind_element("plot_0", object())
    ev.data = 42
    assert set(ev._element_handles()) == {"plot_0"}


def test_repr_distinguishes_elements_from_data():
    ev = Ev()
    ev._bind_element("plot_0", object())
    ev.data = 1
    text = repr(ev)
    assert "plot_0" in text and "data" in text
