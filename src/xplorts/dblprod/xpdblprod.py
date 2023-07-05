"""
Make standalone interactive charts for time series productivity data

When run from the command line, reads data from a CSV file and
creates an HTML document that displays time series levels and cumulative
growth components for one level of a split factor at a time, as well as
a snapshot of growth components across all levels of the split factor for
one time period.

    In the CSV file, the first row of data defines column names.
    The file should include:
        - a column of dates (annual, quarterly or monthly),
        - a column of category names, and
        - one or more columns of data values to be plotted against dates.

    An interactive chart is created, with widgets to select one of the
    category names (from a pulldown list or a slider).  The chart shows
    one line for each value column, with dates plotted along the horizontal
    axis.

    The interactive chart is saved as an HTML file which requires
    a web browser to view, but does not need an active internet connection.
    Once created, the HTML file does not require Python,
    so it is easy to share the interactive chart.

Command line interface
----------------------
usage: dblprod.py [-h] [-b BY] [-d DATE] [-p LPROD] [-v GVA] [-l LABOUR]
                      [-g ARGS] [-t SAVE] [-s]
                      datafile

Create interactive visualiser for labour productivity levels with a split
factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            Show this help message and exit
  -b BY, --by BY        Factor variable for splits
  -d DATE, --date DATE  Date variable
  -p LPROD, --lprod LPROD
                        Productivity variable
  -v GVA, --gva GVA     Gross value added (GVA) variable
  -l LABOUR, --labour LABOUR
                        Labour variable (e.g. jobs or hours worked)
  -g ARGS, --args ARGS  Keyword arguments.  YAML mapping of mappings.  The
                        keys 'lines', 'growth_series' and 'growth_snapshot'
                        can provide keyword arguments to pass to
                        `prod_ts_lines`, `prod_ts_growth` and
                        `prod_growth_snapshot`, respectively.
  -t SAVE, --save SAVE  Interactive .html to save, if different from the
                        datafile base
  -s, --show            Show interactive .html
"""

#%%
# Bokeh imports.
from bokeh.layouts import column, layout, row
from bokeh.models import TabPanel, Tabs
from bokeh.models.widgets import Div
from bokeh.io import save, show
from bokeh import palettes

# Other external imports.
import argparse
from collections import defaultdict
import pandas as pd
from pathlib import Path
import sys
import textwrap
import yaml

# Internal imports.
from ..base import (filter_widget,
                          set_output_file, unpack_data_varnames,
                          variables_cmap)
from ..dutils import growth_vars
from ..heatmap import figheatmap
from . import figprodgrowsnap, figprodlines, figprodgrowts

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
        prog="python -m xplorts.dblprod",
        description="Create interactive visualiser for labour productivity levels with a split factor"
    )
    parser.add_argument("datafile",
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")
    parser.add_argument("-p", "--lprod", type=str,
                        help="Productivity variable")
    parser.add_argument("-v", "--gva",
                        type=str,
                        help="Gross value added (GVA) variable")
    parser.add_argument("-l", "--labour",
                        type=str,
                        help="Labour variable (e.g. jobs or hours worked)")
    parser.add_argument("-g", "--args",
                        type=str,
                        help="""Keyword arguments.  YAML mapping of mappings.  The
                            keys 'lines', 'growth_series' and 'growth_snapshot'
                            can provide keyword arguments to pass to
                            `prod_ts_lines`, `prod_ts_growth` and
                            `prod_growth_snapshot`, respectively.""")

    parser.add_argument("-t", "--save", type=str,
                        help="Interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true",
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of dict of keyword args for various figures.
    # Will return an empty dict for keys not specified in --args option.
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    args.args = defaultdict(dict, args.args)

    return(args)

#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40

def main():
    args = _parse_args()

    # Read the data as is.
    data = pd.read_csv(args.datafile, dtype=str)

    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "lprod", "gva", "labour"],
        data.columns)

    datevar = varnames["date"]
    dependent_variables = [varnames[var] for var in ("lprod", "gva", "labour")]

    title = "xplor lprod: " + Path(args.datafile).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Make palettes.
    color_map = variables_cmap(["labour", "gva", "lprod"],
                               palettes.Category20_3)

    # Convert str to float so we can plot the data.
    data[dependent_variables] = data[dependent_variables].astype(float)


    # Widget for `by`.
    split_widget = filter_widget(data[varnames["by"]], title=varnames["by"])

    # Widget for date.
    date_widget = filter_widget(data[datevar], start_value="last")

    fig_index_lines = figprodlines(
        data,
        varnames=varnames,
        color_map=color_map,
        widget=split_widget,
        height=300, width=600,
        **args.args["lines"])


    # Calculate cumulative growth.
    df_growth_cum = growth_vars(data,
                            date_var=datevar,
                            columns=dependent_variables,
                            by=varnames["by"],
                            baseline="first",
                           )

    fig_ts_growth = figprodgrowts(
        df_growth_cum,
        varnames=varnames,
        color_map=color_map,
        widget=split_widget,
        height=300, width=600,
        **args.args["growth_series"])


    # Calculate period-on-period growth.
    df_growth = growth_vars(data,
                            date_var=datevar,
                            columns=dependent_variables,
                            by=varnames["by"],
                            periods=1,
                           )

    # Truncate long levels of `by`, for axis labels.
    by_var = varnames["by"]
    df_growth[by_var] = df_growth[by_var].apply(
        textwrap.shorten, args=(15,), placeholder='..'
    )

    fig_growth_snapshot = figprodgrowsnap(
        df_growth,
        varnames=varnames,
        color_map=color_map,
        widget=date_widget,
        height=600, width=300,
        **args.args["growth_snapshot"])

    # Put level and growth charts, with widgets, on a tab.
    ts_charts = column(split_widget, fig_index_lines, fig_ts_growth)
    snapshot = column(date_widget, fig_growth_snapshot)
    tab_levels = TabPanel(
        title="Levels",
        child=layout([
            [ts_charts, snapshot],
            ]))


    ## Growth heatmap tab.
    growth_heatmap = figheatmap(
        df_growth,
        x=varnames["date"],
        y=varnames["by"],
        values=varnames["lprod"],
        x_widget=date_widget.handle,
        y_widget=split_widget.handle,
        title=varnames["lprod"] + " growth",
        figure_options=dict(width=900, height=600),
        )
    tab_growth = TabPanel(
        title="Growth heatmap",
        child=row([growth_heatmap, fig_growth_snapshot, date_widget.handle]),
        )


    ## Cumulative growth heatmap tab.
    cum_growth_heatmap = figheatmap(
        df_growth_cum,
        x=varnames["date"],
        y=varnames["by"],
        values=varnames["lprod"],
        x_widget=date_widget.handle,
        y_widget=split_widget.handle,
        title=varnames["lprod"] + " cumulative growth",
        figure_options=dict(width=900, height=600),
        )
    tab_cum_growth = TabPanel(
        title="Cum growth heatmap",
        child=column([cum_growth_heatmap, fig_ts_growth, split_widget.handle]),
        )

    # Make app that shows tabs of various charts.
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        Tabs(tabs=[tab_levels, tab_growth, tab_cum_growth])])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

#%%

if __name__ == "__main__":
    # Running from command line (or in Notebook?).
    sys.exit(main())
