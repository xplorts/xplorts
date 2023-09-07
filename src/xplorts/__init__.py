"""
The xplorts ("explore ts") package contains tools to make
standalone interactive HTML charts to explore time series datasets.

Once created, the HTML documents can be used with any web browser.
They do not need an active internet connection.

Generally the tools work with annual, quarterly, or monthly time series
with a categorical "split factor".  An example would be annual jobs counts
by industry.

The interactive charts provide widgets to select different subsets of
data for display.  A hover tool displays detail for the data under the
cursor.  Chart tools support zoom and plot save.

xplorts uses the [Bokeh](https://bokeh.org) interactive visualization
library.

Command line interface entrypoints
----------------------------------
dblprod
    Create a labour productivity dashboard, with three charts including:
        - a lines chart showing levels of labour productivity, gross value
            added, and labour,
        - a time series growth components chart showing cumulative growth
            in labour productivity, gross value added, and labour, and
        - a snapshot growth components chart showing period-on-period
            growth in labour productivity, gross value added, and labour.

lines
    Create a line chart showing several time series with a split
    factor.  Widgets select one split factor category at a time.

heatmap
    Create a heatmap showing a dependent variable as a function of
    two categorical variables (typically a date variable and a split
    factor).

scatter
    Create scatter chart showing one or more time series with a split
    factor.  Widgets select one split factor category at a time.

snapcomp
    Create a snapshot growth components chart, with a categorical
    vertical axis showing levels of a split factor, horizontal stacked
    bars showing growth components, and markers showing overall growth
    for each stack of bars.  A widget selects one time period at a time.

stacks
    Create stacked bar chart showing several data series with a split
    factor.  Widgets select one split factor at a time (or one time
    period at a time if the split factor is plotted as a chart axis).

tscomp
    Create a time series growth components chart, with time periods
    along the horizontal axis, vertical stacked bars showing growth
    components, and a line showing overall growth.
    Widgets select one split factor category at a time.

utils/*.py
    Extract data from particular datasets to use with xplorts charts.


Modules (exported by the package)
---------------------------------
base
    Miscellaneous helper functions and classes.

dutils
    Miscellaneous data manipulation helpers.

ghostbokeh
    Define an abstract base class to a build pseudo-subclass of a Bokeh class.

heatmap
    Functions to create a heatmap showing data values as a function of
    horizontal and vertical categorical variables.

lines
    Modify a Bokeh Figure by adding line charts to show several time
    series with a split factor.

scatter
    Modify a Bokeh Figure by adding scatter charts to show one or more
    categorical series with a split factor.

slideselect
    Defines a class combining select and slider widgets, with support for
    javascript linking to other objects.

snapcomp
    Modify a Bokeh Figure by adding a snapshot growth components chart, with a
    categorical vertical axis showing levels of a split factor, horizontal
    stacked bars showing growth components, and markers showing overall growth
    for each stack of bars.

stacks
    Modify a Bokeh Figure by adding a horizontal or vertical stacked bar
    chart showing several data series with a split factor.

tscomp
    Modify a Bokeh Figure by adding a time series growth components chart, with
    a categorical vertical axis showing levels of a split factor, horizontal
    stacked bars showing growth components, and a line showing overall growth.


Subpackages (not exported)
--------------------------
dblprod
    Make standalone interactive labour productvity dashboard charts

utils
    Utilities for extracting data from particular datasets to use with
    xplorts charts.
"""

from . import (base, dutils, ghostbokeh,
               slideselect)
# Export API modules within sub-packages.
from .heatmap import heatmap
from .lines import lines
from .scatter import scatter
from .snapcomp import snapcomp
from .stacks import stacks
from .tscomp import tscomp

# Suppress code analysis warnings of unused imports;
#   see https://stackoverflow.com/a/31079085/16327476.
__all__ = ["base", "dutils", "ghostbokeh",
           "heatmap",
           "lines", "scatter",
           "slideselect",
           "snapcomp", "stacks",
           "tscomp"]
