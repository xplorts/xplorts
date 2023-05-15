"""
Make standalone interactive chart showing time series components and total

When run from the command line, reads data from a CSV file and
creates an HTML document that displays time series
growth components for one level of a split factor at a time.
      
    In the CSV file, the first row of data defines column names.  
    The file should include:
        - a column of dates (annual, quarterly or monthly), 
        - a column of category names for the split factor,
        - a column of data values for totals at each date, and 
        - one or more columns of growth components at each date.  

    An interactive chart is created, with widgets to select one of the
    category names (from a pulldown list or a slider).  The chart plots
    dates along the horizontal axis, with growth components shown as stacked
    bars and totals shown as a time series line.
    
    The interactive chart is saved as an HTML file which requires 
    a web browser to view, but does not need an active internet connection.  
    Once created, the HTML file does not require Python,
    so it is easy to share the interactive chart.

Command line interface
----------------------
usage: tscomp.py [-h] [-b BY] [-d DATE] [-l LINE] [-y BARS [BARS ...]]
                 [-g ARGS] [-t SAVE] [-s]
                 datafile

Create interactive time series chart for growth components with a split factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Factor variable for splits
  -d DATE, --date DATE  Date variable
  -l LINE, --line LINE  Variable to show as time series line
  -y BARS [BARS ...], --bars BARS [BARS ...]
                        Variables to show as stacked bars
  -g ARGS, --args ARGS  Keyword arguments. YAML mapping of mappings. The keys
                        'lines' and 'bars' can provide keyword arguments to
                        pass to `ts_components_figure()`.
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
from collections import defaultdict
from pathlib import Path
import pandas as pd
import sys
import yaml

## Imports from this package
from xplorts.tscomp import link_widget_to_tscomp_figure, ts_components_figure
from xplorts.base import (filter_widget, 
                          iv_dv_figure,
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
        prog="python -m xplorts.tscomp",
        description="Create interactive time series chart for growth components with a split factor"
    )
    parser.add_argument("datafile", 
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")

    parser.add_argument("-l", "--line", type=str,
                        help="Variable to show as time series line")
    parser.add_argument("-y", "--bars", 
                        nargs="+", type=str,
                        help="Variables to show as stacked bars")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="""Keyword arguments.  YAML mapping of mappings.  The
                            keys 'lines' and 'bars' 
                            can provide keyword arguments to pass to
                            `ts_components_figure()`.""")

    parser.add_argument("-t", "--save", type=str, 
                        help="Interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true", 
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for ts_components_figure().
    # Will return an empty dict for keys not specified in --args option.
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    args.args = defaultdict(dict, args.args)
    return(args)

#%%

def main():
    # Running from command line.
    
    # Suppress quarterly or monthly axis labels for time series longer than this.
    DATE_THRESHOLD = 40
    
    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)
    
    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "line", "bars"],
        data.columns)
    datevar = varnames["date"]
    datavars = varnames["bars"]
    linevar = varnames["line"]
    dependent_variables = datavars.copy()
    if linevar is not None:
        dependent_variables.insert(0, linevar)

    data_local = data.copy()
    data_local["_date_factor"] = date_tuples(data_local[datevar],
                                             length_threshold=DATE_THRESHOLD)

    # Prepare to suppress most quarters or months on axis if lots of them.
    suppress_factors = (isinstance(data_local["_date_factor"][0], tuple)
                        and len(data_local["_date_factor"].unique()) > DATE_THRESHOLD)
    
    title = "tscomp: " + Path(args.datafile).stem
    
    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Map variables to colors.
    default_color_map = variables_cmap(dependent_variables[::-1],
                               palettes.Category20_20)
    default_bar_colors = [default_color_map[var] for var in datavars]

    fig = iv_dv_figure(
        iv_data = data_local["_date_factor"].unique(),
        iv_axis = "x",
        suppress_factors = suppress_factors,
        title = "Time series components and total",
        #x_axis_label = kwargs.pop("x_axis_label", date),
        #y_axis_label = kwargs.pop("y_axis_label", "Value"),
   )
    
    if linevar is None:
        line_args = {}
    else:
        # Use specified line args, else defaults.
        line_args = args.args.pop(
            "lines",
            {"color": default_color_map[linevar]})
        
    # Use specified bar args, else defaults.
    bar_args = args.args.pop(
        "bars",
        {"color": default_bar_colors})

    # Make chart, and link widget to make one factor level visible.
    ts_components_figure(
        fig,
        data_local,
        by=varnames["by"],
        line_variable=linevar,
        date_variable=dict(plot="_date_factor", hover=datevar),
        bar_variables=datavars,
        line_args=line_args,
        bar_args=bar_args,
        **args.args)

    # Widget for `by`.
    widget = filter_widget(data[varnames["by"]], title=varnames["by"])
    link_widget_to_tscomp_figure(widget, fig)

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


if __name__ == "__main__":
    sys.exit(main())
