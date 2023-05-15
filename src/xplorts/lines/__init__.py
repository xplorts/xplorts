"""
Make standalone interactive line charts for time series data

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.lines


Command line interface
----------------------
> python -m xplorts.lines --help
"""

# Export names from .lines.lines.
from .lines import grouped_multi_lines, link_widget_to_lines

__all__ = ["grouped_multi_lines", "link_widget_to_lines"]
