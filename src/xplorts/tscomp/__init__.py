"""
Make standalone interactive chart showing time series components and total

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.tscomp


Command line interface
----------------------
> python -m xplorts.tscomp --help
"""

# Export names from .tscomp.tscomp.
from .tscomp import link_widget_to_tscomp_figure, ts_components_figure
from .xptscomp import figtscomp

__all__ = ["figtscomp", "link_widget_to_tscomp_figure", "ts_components_figure"]
