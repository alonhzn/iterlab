"""Written by iterlab. Rewritten whenever you change the interface.

This is your interface: what you drew, and the class that lets your editor
complete `ev.` inside a handler.

iterlab reads this file without importing it - the layout below is lifted out
and evaluated as literals - so every value in it has to be written out rather
than computed.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from iterlab.types import Axes, Button, Label, NumberBox, TextBox

LAYOUT = {
    'schema_version': 8,
    'iterlab_version': '2.0.1',
    'window': {'width': 1120, 'height': 700},
    'toolbar_collapsed': False,
    'elements': {
        'lbl_title': {
            'type': 'label',
            'position': [0.03, 0.93, 0.55, 0.05],
            'label': 'Signal explorer',
            'style': {'font_size': 15, 'bold': True, 'align': 'left'},
        },
        'lbl_status': {
            'type': 'label',
            'position': [0.6, 0.93, 0.37, 0.05],
            'label': '',
            'style': {'text_color': '#5c6470', 'align': 'right'},
        },
        'ax_waves': {'type': 'axes', 'position': [0.03, 0.52, 0.6, 0.39]},
        'ax_scatter': {'type': 'axes', 'position': [0.66, 0.52, 0.31, 0.39]},
        'ax_bars': {'type': 'axes', 'position': [0.03, 0.15, 0.6, 0.33]},
        'lbl_freq': {
            'type': 'label',
            'position': [0.66, 0.44, 0.31, 0.04],
            'label': 'Frequencies (Hz)',
            'style': {'align': 'left'},
        },
        'edt_freq': {'type': 'text_box', 'position': [0.66, 0.38, 0.31, 0.05], 'label': '1, 2.5, 4'},
        'lbl_points': {
            'type': 'label',
            'position': [0.66, 0.31, 0.14, 0.04],
            'label': 'Samples',
            'style': {'align': 'left'},
        },
        'val_points': {'type': 'number_box', 'position': [0.81, 0.31, 0.16, 0.05], 'label': '240'},
        'lbl_noise': {
            'type': 'label',
            'position': [0.66, 0.24, 0.14, 0.04],
            'label': 'Noise',
            'style': {'align': 'left'},
        },
        'val_noise': {'type': 'number_box', 'position': [0.81, 0.24, 0.16, 0.05], 'label': '0.25'},
        'cmd_redraw': {'type': 'button', 'position': [0.66, 0.15, 0.15, 0.06], 'label': 'Redraw'},
        'cmd_shuffle': {'type': 'button', 'position': [0.82, 0.15, 0.15, 0.06], 'label': 'Shuffle'},
        'cmd_reset': {'type': 'button', 'position': [0.03, 0.05, 0.14, 0.06], 'label': 'Reset'},
        'lbl_hint': {
            'type': 'label',
            'position': [0.2, 0.05, 0.77, 0.05],
            'label': 'Edit showcase.py and click Redraw - the data stays loaded',
            'style': {'text_color': '#5c6470', 'align': 'left'},
        },
    },
}


class Ev:
    """Your interface, as your editor sees it."""

    lbl_title: "Label"
    lbl_status: "Label"
    ax_waves: "Axes"
    ax_scatter: "Axes"
    ax_bars: "Axes"
    lbl_freq: "Label"
    edt_freq: "TextBox"
    lbl_points: "Label"
    val_points: "NumberBox"
    lbl_noise: "Label"
    val_noise: "NumberBox"
    cmd_redraw: "Button"
    cmd_shuffle: "Button"
    cmd_reset: "Button"
    lbl_hint: "Label"

    # `ev` is yours to fill as well: these keep your own attributes from reading
    # as errors, while the elements above keep their types.
    def __getattr__(self, name: str): ...

    def __setattr__(self, name: str, value) -> None: ...
