"""
Make standalone interactive line charts for time series data.

When run from the command line, `xplines` reads data from a `csv` file and
creates an HTML document that displays an interactive line chart.

    In the `csv` file, the first row of data defines column names.
    The file should include:
        - a column of dates (annual, quarterly or monthly),
        - a column of category names, and
        - one or more columns of data values to be plotted against dates.

    An interactive chart is created, with widgets to select one of the
    category names (from a pulldown list or a slider).  The chart shows
    one line for each value column, with dates plotted along the horizontal
    axis.

Functions
---------
figlines
    Make interactive line chart of time series data with split factor

Constants
---------
DATE_THRESHOLD
    Suppress quarterly or monthly axis labels for time series longer than this


Command line interface
----------------------
usage: xplines.py [-h] [-b BY] [-d DATEVAR] [-l LINES [LINES ...]]
                               [-g ARGS] [-p PALETTE] [-t SAVE | -T] [-s]
                                datafile

Create interactive charts for time series data split by a factor

positional arguments:
  datafile              Name of .csv file with time series data split by a
                        factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Name of factor variable
  -d DATE, --date DATE
                        Name of date variable
  -l LINES [LINES ...], --lines LINES [LINES ...]
                        Variables to show as time series lines
  -g ARGS, --args ARGS  Keyword arguments for grouped_multi_lines()
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -s, --show            Show interactive .html
"""

#%%
from bokeh.io import save, show
from bokeh.layouts import layout
from bokeh.models.widgets import Div

import argparse
import pandas as pd
from pathlib import Path
import sys
import yaml

# Internal imports.
from xplorts.lines import grouped_multi_lines, link_widget_to_lines

from xplorts.base import (filter_widget, iv_dv_figure,
                          set_output_file, unpack_data_varnames,
                          variables_cmap)
from xplorts.dutils import date_tuples

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
        prog="python -m xplorts.lines",
        description="Create interactive line charts for time series data with a split factor"
    )
    parser.add_argument("datafile",
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")
    parser.add_argument("-l", "--lines",
                        nargs="+", type=str,
                        help="Variables to show as time series lines")
    parser.add_argument("-g", "--args",
                        type=str,
                        help="Keyword arguments for grouped_multi_lines(), specified as YAML mapping")

    parser.add_argument("-t", "--save", type=str,
                        help="Name of interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true",
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for grouped_multi_lines().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)


#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40

#%%

def figlines(data, *,
            date,
            by,
            data_variables,
            widget=None,
            color_map=None,
            line_dash=None,
            iv_dv_args=dict(),
            **kwargs):
    """
    Make interactive line chart of time series data with split factor

    Parameters
    ----------
    data : DataFrame
        Including columns to be plotted, which are named in other parameters.
    date : str
        Name of column containing time series dates to plot along the horizontal
        chart axis.
    by : str
        Name of column containing split levels.  The chart displays a single split
        level at a time.
    data_variables : list
        List of column names to be plotted as time series lines.
    widget : Bokeh widget, optional
        The `value` attribute will be linked to the chart to make visible one
        value of the `by` variable.
    color_map : dict of colors, optional
        Map data_variables to colors.
    line_dash : list of line dash specifications, optional
        For corresponding data_variables.
    iv_dv_args : mapping
        Keyword arguments passed to `iv_dv_figure()`.
    kwargs : mapping
        Keyword arguments passed to `grouped_multi_lines()`.

    Returns
    -------
    Bokeh figure.
    """

    # Transform monthly and quarterly dates to nested categories.
    data_local = data.copy()
    data_local["_date_factor"] = date_tuples(data_local[date],
                                             length_threshold=DATE_THRESHOLD)

    # Prepare to suppress most quarters or months on axis if lots of them.
    suppress_factors = (isinstance(data_local["_date_factor"][0],
                                   tuple)
                        and len(data_local["_date_factor"].unique())
                            > DATE_THRESHOLD)

    # Make empty figure for time series line chart.
    fig_index_lines = iv_dv_figure(
        iv_data = data_local["_date_factor"],
        iv_axis = "x",
        suppress_factors = suppress_factors,
        title = "Time series levels",
        # Use our own default label for y axis if none given.
        y_axis_label = iv_dv_args.pop("y_axis_label", "Value"),
        **iv_dv_args
    )

    if color_map is None:
        color_map = variables_cmap(data_variables,
                                   "Category20_20")
    palette = [color_map[var] for var in data_variables]

    if line_dash is None:
        # Use dash for alternating line colors (but last one is always solid).
        line_dash = ["solid"] * len(data_variables)
        line_dash[0:-1:2] = ["dashed"] * len(data_variables[0:-1:2])

    cds_options = {
        "color": palette,
        "line_dash": line_dash}

    index_lines = grouped_multi_lines(
        fig_index_lines,
        data_local,
        iv_variable=dict(plot="_date_factor", hover=date),
        data_variables=data_variables,
        by=by,
        # default keyword args can be overridden by kwargs.
        cds_options = kwargs.pop("cds_options", cds_options),
        color = kwargs.pop("color", "color"),
        line_dash = kwargs.pop("line_dash", "line_dash"),
        line_alpha = kwargs.pop("line_alpha", 0.8),
        hover_line_alpha = kwargs.pop("hover_line_alpha", 1),
        line_width = kwargs.pop("line_width", 2),
        hover_line_width = kwargs.pop("hover_line_width", 4),
        **kwargs
    )

    if widget is not None:
        link_widget_to_lines(widget, index_lines)
    return fig_index_lines


#%%

def main():
    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)

    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "lines"],
        data.columns)
    datavars = varnames["lines"]

    title = "lines: " + Path(args.datafile).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Convert str to float so we can plot the data.
    data[datavars] = data[datavars].astype(float)

    # Make a slide-select widget to choose industry.
    split_widget = filter_widget(data[varnames["by"]], title=varnames["by"])


    fig = figlines(data,
                    widget=split_widget,
                    date=varnames["date"],
                    by=varnames["by"],
                    data_variables=datavars)

    # Make app that shows widget and chart.
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        [split_widget],
        [fig]
    ])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.


if __name__ == "__main__":
    sys.exit(main())
