"""
Make standalone interactive line charts for time series data

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.lines

Functions
---------
figlines
    Create figure with time series lines
grouped_multi_lines
    Add time series lines to a figure
link_widget_to_lines
    Link a widget to time series lines (usually to select a split level)


Command line interface
----------------------
> python -m xplorts.lines --help
"""

# Export names from .lines.lines.
from .lines import grouped_multi_lines, link_widget_to_lines
from .xplines import figlines

__all__ = ["figlines", "grouped_multi_lines", "link_widget_to_lines"]
