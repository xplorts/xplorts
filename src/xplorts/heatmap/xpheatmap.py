"""
Make a standalone app showing an interactive heatmap in a web browser

When run from the command line, reads data from a CSV file and
creates an HTML document that displays a heatmap of values as a
function of categical x and y variables.

    In the CSV file, the first row of data defines column names.
    The file should include:
        - a column of dates (annual, quarterly or monthly),
        - a column of category names, and
        - a column of data values to be plotted.

    An interactive chart is created.  The chart shows a heatmap with dates
    along the horizontal axis, category names along the vertical axis,
    and cell colors reflecting data values.

    The interactive chart is saved as an HTML file which requires
    a web browser to view, but does not need an active internet connection.
    Once created, the HTML file does not require Python,
    so it is easy to share the interactive chart.

Command line interface
----------------------
usage: python -m xplorts.heatmap [-h] [-x DATE] [-y BY] [-z VALUES] [-g ARGS] [-t SAVE] [-s] datafile

Create interactive heatmap for time series data with a split factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -x DATE, --date DATE  Name of categorical variable for horizontal axis
  -y BY, --by BY        Name of categorical split variable for vertical axis
  -z VALUES, --values VALUES
                        Name of numeric variable to show as heatmap color
  -g ARGS, --args ARGS  Keyword arguments for figheatmap(), as a YAML mapping.
  -t SAVE, --save SAVE  Interactive .html to save, if different from the datafile base
  -s, --show            Show interactive .html
"""

#%%

from bokeh.io import save, show
from bokeh.layouts import layout
from bokeh.models import Div

import argparse
from pathlib import Path
import pandas as pd
import sys
import yaml

from xplorts.base import set_output_file, unpack_data_varnames
from xplorts.heatmap import figheatmap

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
        prog="python -m xplorts.heatmap",
        description="Make a standalone app showing an interactive heatmap in a web browser"
    )
    parser.add_argument("datafile",
                        help="File (CSV) with data series and split factor")

    parser.add_argument("-x", "--date", type=str,
                        help="Name of categorical variable for horizontal axis")

    parser.add_argument("-y", "--by", type=str,
                        help="Name of categorical split variable for vertical axis")

    parser.add_argument("-z", "--values", type=str,
                        help="Name of numeric variable to show as heatmap color")

    parser.add_argument("-g", "--args",
                        type=str,
                        help="""Keyword arguments for figheatmap(), as a YAML mapping.""")

    parser.add_argument("-t", "--save", type=str,
                        help="Interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true",
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for ts_components_figure().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)


#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40

def main():
    """Entry point for heatmap command line"""

    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)

    title = "heatmap: " + Path(args.datafile).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "values"],
        data.columns)

    # Convert str to float so we can plot the data.
    dependent_variables = varnames["values"]
    data[dependent_variables] = data[dependent_variables].astype(float)

    fig = figheatmap(
        data,
        x=varnames["date"],
        y=varnames["by"],
        values=varnames["values"],
        title=(varnames["values"] + " by " + varnames["by"]
               + " as function of " + varnames["date"]),
        figure_options=dict(width=900, height=600),
        )

    # Make app that shows heatmap.
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        [fig],
    ])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

if __name__ == "__main__":
    sys.exit(main())
