"""
Make standalone interactive labour productvity dashboard charts

This sub-package exposes Python modules, and provides a command line interface 
entry point.


Application program interface
-----------------------------
>>> import xplorts.dblprod

Functions
---------
figprodgrowsnap
figprodlines
figprodgrowts


Command line interface
----------------------
> python -m xplorts.dblprod --help
"""

# Export names.
from .prodgrowsnap import figprodgrowsnap
from .prodlines import figprodlines
from .prodgrowts import figprodgrowts

__all__ = ["figprodgrowsnap", "figprodlines", "figprodgrowts"]
