#!/usr/bin/env python
# coding: utf-8
"""
tscomp
------
Make standalone interactive chart showing time series components and total.

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, `tscomp.py` reads data from a CSV file and
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


Application program interface (API)
-----------------------------------
ts_components_figure
    Interactive chart showing time series components and total by split group

link_widget_to_tscomp_figure
    Link a select widget to components series to show one level of split group
"""

#%%
from bokeh.layouts import layout
from bokeh.io import save, show
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Div
from bokeh import palettes

import argparse
from collections import defaultdict
from pathlib import Path
import pandas as pd
import yaml

from base import (add_hover_tool, factor_view, filter_widget, 
                  iv_dv_figure, link_widgets_to_groupfilters,
                  set_output_file, unpack_data_varnames, 
                  variables_cmap)
from dutils import date_tuples
from lines import grouped_multi_lines, link_widget_to_lines
from stacks import grouped_stack

#%%
def ts_components_figure(
    fig,
    data,
    date_variable,
    bar_variables,
    by=None,
    line_variable=None,
    line_args={},
    bar_args={},
):
    """
    Interactive chart showing time series components and total by split group
    
    Parameters
    ----------
    date_variable: str or dict
        If str, the name of a data column, which will be shown on the horizontal
        axis.  
        
        If dict, should map key "plot" to a variable to show on the
        horizontal axis and should map key "hover" to a corresponding variable
        to display in hover information.  This is often useful when displaying
        quarterly dates as nested categories like `("2020", "Q1")`.    

    """

    # Make line chart first, for sake of legend.
    lines = grouped_multi_lines(
        fig,
        data,
        iv_variable=date_variable,
        data_variables=line_variable,
        by=by,
        **line_args
    )

    source = ColumnDataSource(data)    
    view_by_factor = factor_view(source, by)
    
    # Make stacked bars showing components.
    bars = grouped_stack(
        fig,
        iv_axis="x",
        iv_variable=date_variable,
        bar_variables=bar_variables,
        source=source,
        view=view_by_factor,
        **bar_args,
    )
    
    ## Define hover info for whole figure.    
    if isinstance(date_variable, dict):
        iv_hover_variable = date_variable["hover"]
    else:
        iv_hover_variable = date_variable

    tooltips = [(by, f"@{{{by}}}"),
                (iv_hover_variable, f"@{{{iv_hover_variable}}}")]
    if line_variable is not None:
        tooltips.append(
            (line_variable, f"@{{{line_variable}}}{{0[.]0 a}}")
        )
    tooltips.extend((bar, f"@{{{bar}}}{{0[.]0 a}}") for bar in bar_variables)
    
    hover = add_hover_tool(fig, 
                           bars[0:1],  # Show tips just once for the stack, not for every glyph.
                           *tooltips,
                           name="Hover bar stack",
                           description="Hover bar stack",
                           mode="vline",
                           point_policy = 'follow_mouse',
                           attachment="horizontal",
                           show_arrow = False,
                          )
    
    if fig.toolbar.active_inspect == "auto":
        # Activate just the new hover tool.
        fig.toolbar.active_inspect = hover
    else:
        # Add the new hover to list of active inspectors.
        fig.toolbar.active_inspect = fig.toolbar.active_inspect.append(hover)    
    
    fig._lines = lines
    fig._stacked = bars
    
    return lines + bars

#%%
def link_widget_to_tscomp_figure(widget, fig=None, lines=None, bars=None):
    """
    
    """
    if lines is None:
        lines = fig._lines
    if bars is None:
        bars = fig._stacked
    source = bars[0].data_source
    view = bars[0].view
    link_widget_to_lines(widget, lines)
    link_widgets_to_groupfilters(widget,
                                 source=source, 
                                 view=view)

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

if __name__ == "__main__":
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

