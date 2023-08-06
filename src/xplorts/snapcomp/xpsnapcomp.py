"""
Make standalone chart showing horizontal snapshot components and total.

When run from the command line, reads data from a CSV file and
creates an HTML document that displays snapshot
components for one level of a split factor at a time.

    In the CSV file, the first row of data defines column names.
    The file should include:
        - a column of category names for the vertical chart axis,
        - a column of category names for the split factor
        - a column of data totals at each level along the vertical axis, and
        - one or more columns of value components for each total.

    An interactive chart is created, with widgets to select one of the
    split factor levels (from a pulldown list or a slider).  The chart plots
    value components as horizontal stacked bars with a marker for each total.

    The interactive chart is saved as an HTML file which requires
    a web browser to view, but does not need an active internet connection.
    Once created, the HTML file does not require Python,
    so it is easy to share the interactive chart.

Command line interface
----------------------
usage: snapcomp.py [-h] [-b BY] [-y IV] [-m MARKERS] [-x BARS [BARS ...]] [-L]
                   [-g ARGS] [-t SAVE] [-s]
                   datafile

Create interactive horizontal bar chart for snapshot components with a split
factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Factor variable for splits
  -y IV, --iv IV        Name of independent categorical variable for vertical
                        axis
  -m MARKERS, --markers MARKERS
                        Variable to show as marker points
  -x BARS [BARS ...], --bars BARS [BARS ...]
                        Variables to show as horizontal stacked bars
  -L, --last            Initial chart shows last level of `by` variable
  -g ARGS, --args ARGS  Keyword arguments. YAML mapping of mappings. The keys
                        'lines' and 'bars' can provide keyword arguments to
                        pass to `components_figure()`.
  -t SAVE, --save SAVE  Interactive .html to save, if different from the
                        datafile base
  -s, --show            Show interactive .html

"""

#%%

from bokeh.layouts import layout
from bokeh.io import save, show
from bokeh.models.widgets import Div
from bokeh import palettes

import argparse
from pathlib import Path
import pandas as pd
import sys
import yaml

## Imports from this package
from xplorts.snapcomp import components_figure, link_widget_to_snapcomp_figure
from xplorts.base import (iv_dv_figure, filter_widget,
                          set_output_file,
                          unpack_data_varnames, variables_cmap)

#%%

def _parse_args():
    """
    Parse command line arguments

    Returns
    -------
    `argparse.Namespace` object

    Examples
    --------
    args = _parse_args()
    data = pd.read_csv(args.datafile)

    Resources
    ---------
    [argparse — Parser for command-line options, arguments and sub-commands](https://docs.python.org/3/library/argparse.html#dest)
    """
    # Check command line arguments.
    parser = argparse.ArgumentParser(
        prog="python -m xplorts.snapcomp",
        description="Create interactive horizontal bar chart for snapshot components with a split factor"
    )
    parser.add_argument("datafile",
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for time series splits, shown on vertical axis")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable for choosing one snapshot at a time")

    parser.add_argument("-m", "--markers", type=str,
                        help="Variable to show as marker points")
    parser.add_argument("-x", "--bars",
                        nargs="+", type=str,
                        help="Variables to show as horizontal stacked bars")

    parser.add_argument("-L", "--last", action="store_true",
                        help="Initial chart shows last level of `date` variable")

    parser.add_argument("-g", "--args",
                        type=str,
                        help="""Keyword arguments.  YAML mapping of mappings.  The
                            keys 'lines' and 'bars'
                            can provide keyword arguments to pass to
                            `components_figure()`.""")

    parser.add_argument("-t", "--save", type=str,
                        help="Interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true",
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for ts_components_figure().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)

#%%

def figsnapcomp(data,
                *,
                date,
                by,
                bars=None,
                markers=None,
                widget=None,
                color_map=None,
                iv_dv_args=dict(),
                **kwargs):
    """
    Make snapshot horizontal bar chart of time series growth components

    Parameters
    ----------
    data : DataFrame
        Including columns to be plotted, which are named in other parameters.
    date : str
        Name of column containing time series dates.  The chart displays a single
        date at a time.  If not given, `varnames["date"]` is used.
    by : str
        Name of column containing split levels, which are displayed along the vertical
        axis as a categorical independent variable.  If not given, `varnames["by"]` is
        used.
    bars : [str]
        Names of columns containing values to be plotted as horizontal stacked
        bars.
    markers : str, optional
        Name of column containing values to be plotted as markers.
    widget : Bokeh widget, optional
        The `value` attribute will be linked to the chart to make visible one
        value of the `date` variable.
    iv_dv_args : mapping
        Keyword arguments passed to `iv_dv_figure()`.
    kwargs : mapping
        Keyword arguments passed to components_figure().

    Returns
    -------
    Bokeh figure.
    """

    ## Show snapshot of latest growth components as hbars by industry.
    fig_snapshot = iv_dv_figure(
        iv_data = reversed(data[by].unique()),  # From top down.
        iv_axis = "y",
        x_axis_label = iv_dv_args.pop("y_axis_label", "Value"),
        y_axis_label = iv_dv_args.pop("x_axis_label", by),
        legend_place = "above",
        **iv_dv_args
    )

    if isinstance(bars, str):
        # Put single string in a list as a convenience.
        bars = [bars]
    dependent_variables = bars if markers is None else [markers] + bars

    if color_map is None:
        # Use special color for markers.
        c20 = palettes.Category20_20
        category_colors = c20[2:3] + c20[:2] + c20[4:]
        color_map = variables_cmap(dependent_variables,
                                   category_colors)
    palette = [color_map[var] for var in dependent_variables]

    components_figure(
        fig_snapshot,
        data,
        by=date,
        marker_variable=markers,
        y=by,
        bar_variables=bars,
        scatter_args = {} if markers is None else {"color": palette[0]},
        bar_args={"color": palette if markers is None else palette[1:]},
    )

    if widget is not None:
        link_widget_to_snapcomp_figure(widget, fig_snapshot)

    return fig_snapshot


#%%

def main():
    # Running from command line.
    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)

    title = "snapcomp: " + Path(args.datafile).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["by", "date", "markers", "bars"],
        data.columns)

    # Make list of dependent variables for bars plus markers, if any.
    markers = varnames["markers"]
    bars = varnames["bars"]
    if isinstance(bars, str):
        # Put single string in a list as a convenience.
        bars = [bars]
    dependent_variables = bars if markers is None else [markers] + bars

    # Convert str to float so we can plot the data.
    data[dependent_variables] = data[dependent_variables].astype(float)

    iv_dv_args = args.args.pop("iv_dv_args", {})
    iv_dv_args.update(height=600, width=300)

    # Widget for `date`.
    date = varnames["date"]
    widget = filter_widget(data[date], title=date)
    if args.last:
        # Make initial view show snapshot for last date rather than first.
        widget.value = widget.options[-1]

    fig = figsnapcomp(
        data,
        by=varnames["by"],
        date=date,
        bars=bars,
        markers=markers,
        widget=widget,
        iv_dv_args=iv_dv_args,
        **args.args)

    # Make app that shows widget and chart.
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        [widget],
        [fig]
    ])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

#%%
if __name__ == "__main__":
    sys.exit(main())
