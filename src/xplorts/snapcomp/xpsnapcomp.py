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
                        help="Factor variable for splits")

    parser.add_argument("-y", "--iv", type=str,
                        help="Name of independent categorical variable for vertical axis")

    parser.add_argument("-m", "--markers", type=str,
                        help="Variable to show as marker points")
    parser.add_argument("-x", "--bars",
                        nargs="+", type=str,
                        help="Variables to show as horizontal stacked bars")

    parser.add_argument("-L", "--last", action="store_true",
                        help="Initial chart shows last level of `by` variable")

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
        ["iv", "by", "markers", "bars"],
        data.columns)

    # Make list of dependent variables for bars plus markers, if any.
    markervar = varnames["markers"]
    dependent_variables = varnames["bars"].copy()
    if markervar is not None:
        dependent_variables.insert(0, markervar)

    # Convert str to float so we can plot the data.
    data[dependent_variables] = data[dependent_variables].astype(float)

    default_color_map = variables_cmap(dependent_variables[::-1],
                                       palettes.Category20_20)
    default_bar_colors = [default_color_map[var] for var in varnames["bars"]]

    fig = iv_dv_figure(
        iv_data = reversed(data[varnames["iv"]].unique()),
        iv_axis = "y",
    )

    if markervar is None:
        scatter_args = {}
    else:
        # Use specified scatter_args, else defaults.
        scatter_args = args.args.pop(
            "scatter_args",
            {"color": default_color_map[markervar]})

    # Use specified bar_args, else defaults.
    bar_args = args.args.pop(
        "bar_args",
        {"color": default_bar_colors})

    # Make chart, and link widget to make one factor level visible.
    renderers = components_figure(
        fig,
        data,
        by=varnames["by"],
        marker_variable=varnames["markers"],
        y=varnames["iv"],
        bar_variables=varnames["bars"],
        scatter_args=scatter_args,
        bar_args=bar_args,
        **args.args)

    # Widget for `by`.
    byvar = varnames["by"]
    widget = filter_widget(data[byvar], title=byvar)
    if args.last:
        widget.value = widget.options[-1]
    link_widget_to_snapcomp_figure(widget, fig)

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
