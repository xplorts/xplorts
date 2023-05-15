"""
Make standalone interactive scatter charts for time series data

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.scatter


Command line interface
----------------------
> python -m xplorts.scatter --help
"""

# Export names from .lines.lines.
from .scatter import grouped_scatter

__all__ = ["grouped_scatter"]
