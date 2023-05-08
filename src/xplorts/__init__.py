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

Scripts
-------
lines.py
    Create a line chart showing several time series with a split
    factor.  Widgets select one split factor category at a time.
    
scatter.py
    Create scatter chart showing one or more time series with a split
    factor.  Widgets select one split factor category at a time.

snapcomp.py
    Create a snapshot growth components chart, with a categorical
    vertical axis showing levels of a split factor, horizontal stacked 
    bars showing growth components, and markers showing overall growth
    for each stack of bars.  A widget selects one time period at a time.

stacks.py
    Create stacked bar chart showing several data series with a split
    factor.  Widgets select one split factor at a time (or one time
    period at a time if the split factor is plotted as a chart axis).

tscomp.py
    Create a time series growth components chart, with time periods
    along the horizontal axis, vertical stacked bars showing growth
    components, and a line showing overall growth.
    Widgets select one split factor category at a time.

xplor_lprod.py
    Create a labour productivity dashboard, with three charts including:
        - a lines chart showing levels of labour productivity, gross value 
            added, and labour,
        - a time series growth components chart showing cumulative growth
            in labour productivity, gross value added, and labour, and
        - a snapshot growth components chart showing period-on-period
            growth in labour productivity, gross value added, and labour.

utils/*.py
    Extract data from particular datasets to use with xplorts charts.


Modules (exported by the package)
---------------------------------
base
    Miscellaneous helper functions and classes.

ghostbokeh
    Define an abstract base class to a build pseudo-subclass of a Bokeh class.

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

xplor_lprod
    Modify a Bokeh Figure by adding charts to show labour productivity
    levels or growth components.


Subpackages (not exported)
--------------------------
utils
    Utilities for extracting data from particular datasets to use with
    xplorts charts.
"""

from . import (base, bokeh_stacks, dutils, ghostbokeh, lines, scatter, 
               slideselect, snapcomp, stacks, stacks_util,
               tscomp, xplor_lprod)

# Suppress code analysis warnings of unused imports; 
#   see https://stackoverflow.com/a/31079085/16327476.
__all__ = ["base", "bokeh_stacks", "dutils", "ghostbokeh", "lines", "scatter", 
           "slideselect", "snapcomp", "stacks", "stacks_util",
           "tscomp", "xplor_lprod"]
