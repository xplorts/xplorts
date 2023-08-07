"""
Make interactive snapshot growth composition charts for time series data

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.snapcomp


Command line interface
----------------------
> python -m xplorts.snapcomp --help
"""

# Export names from .snapcomp.snapcomp.
from .snapcomp import components_figure, link_widget_to_snapcomp_figure
from .xpsnapcomp import figsnapcomp

__all__ = ["components_figure", "figsnapcomp", "link_widget_to_snapcomp_figure"]
