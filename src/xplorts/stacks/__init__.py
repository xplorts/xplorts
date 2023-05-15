"""
Make standalone interactive stacked bar charts for categorical data

This sub-package provides a module that can be imported as a Python
module, and a command line interface entry point.


Application program interface
-----------------------------
>>> import xplorts.stacks


Command line interface
----------------------
> python -m xplorts.stacks --help
"""

# Export names from .stacks.stacks.
from .stacks import grouped_stack

__all__ = ["grouped_stack"]
