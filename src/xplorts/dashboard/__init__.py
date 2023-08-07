"""
Make standalone interactive time series dashboard charts

This sub-package exposes Python modules, and provides a command line interface
entry point.


Application program interface
-----------------------------
>>> import xplorts.dashboard

Functions
---------
dashboard_tabs
    Create tabs of figures and widgets to explore time series data

Command line interface
----------------------
> python -m xplorts.dashboard --help
"""

# Export names.
from xplorts.dashboard.xpdashboard import dashboard_tabs

__all__ = ["dashboard_tabs"]
