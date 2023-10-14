"""
Make interactive revision heatmaps

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.diff


Command line interface
----------------------
> xp-diff --help

or

> python -m xplorts.diff --help
"""

# Export names from .diff.diff.
from .diff import (DIFF_KEYS, RevisedTS, link_widget_to_heatmaps,
                     revision_layout, revtab)
from .xpdiff import difftabs

__all__ = ["DIFF_KEYS", "RevisedTS", "difftabs", "link_widget_to_heatmaps",
           "revision_layout", "revtab"]
