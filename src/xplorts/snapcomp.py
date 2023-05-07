#!/usr/bin/env python
# coding: utf-8
"""
Make standalone interactive chart showing snapshot components and total.

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, `snapcomp.py` reads data from a CSV file and
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
    value components as stacked bars with a marker for each total.
    
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


Application program interface (API)
-----------------------------------
components_figure
    Interactive chart showing snapshot components and total by split group

link_widget_to_snapcomp_figure
    Link a select widget to components to show one level of split group
"""

#%%

from bokeh.layouts import layout
from bokeh.io import save, show
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Div
from bokeh import palettes

import argparse
from pathlib import Path
import pandas as pd
import yaml

from xplorts.base import (add_hover_tool, factor_view, iv_dv_figure, filter_widget, 
                          link_widgets_to_groupfilters, set_output_file, 
                          unpack_data_varnames, variables_cmap)
from xplorts.scatter import grouped_scatter
from xplorts.stacks import grouped_stack

#%%

def components_figure(
    fig,
    data,
    y,
    bar_variables,
    by=None,
    marker_variable=None,
    scatter_args={},
    bar_args={},
):
    """
    Interactive chart showing snapshot components and total by split group
    """

    source = ColumnDataSource(data)    
    view_by_factor = factor_view(source, by)

    # Make scatter chart first, for sake of legend.
    markers = grouped_scatter(
        fig,
        iv_axis="y",
        iv_variable=y,
        marker_variable=marker_variable,
        source=source,
        view=view_by_factor,
        **scatter_args
    )
    fig._scatter = [markers]
    
    # Make stacked bars showing components.
    tooltips = ([] if marker_variable is None 
                else             
                    # Show value of line, regardless.
                    [(marker_variable, f"@{marker_variable}{{0,0.0}}")]
               )
    bars = grouped_stack(
        fig,
        iv_axis="y",
        iv_variable=y,
        bar_variables=bar_variables,
        source=source,
        view=view_by_factor,
        #tooltips=tooltips,
        **bar_args,
    )
    fig._stacked = bars
    
    ## Define hover info for whole figure.    
    if isinstance(y, dict):
        iv_hover_variable = y["hover"]
    else:
        iv_hover_variable = y

    tooltips = [(by, f"@{{{by}}}"),
                (iv_hover_variable, f"@{{{iv_hover_variable}}}")]
    if marker_variable is not None:
        tooltips.append(
            (marker_variable, f"@{{{marker_variable}}}{{0[.]0 a}}")
        )
    tooltips.extend((bar, f"@{{{bar}}}{{0[.]0 a}}") for bar in bar_variables)
    
    hover = add_hover_tool(fig, 
                           bars[0:1],  # Show tips just once for the stack, not for every glyph.
                           *tooltips,
                           name="Hover bar stack",
                           description="Hover bar stack",
                           mode="hline",
                           point_policy = 'follow_mouse',
                           attachment="vertical",
                           show_arrow = False,
                          )
    
    if fig.toolbar.active_inspect == "auto":
        # Activate just the new hover tool.
        fig.toolbar.active_inspect = hover
    else:
        # Add the new hover to list of active inspectors.
        fig.toolbar.active_inspect = fig.toolbar.active_inspect.append(hover)    

    return [markers] + bars

#%%

def link_widget_to_snapcomp_figure(widget, fig=None, renderers=None):
    if renderers is None:
        # Use first set of stacked bars.
        sample = fig._stacked[0]
    elif isinstance(renderers, list):
        # Use first renderer.
        sample = renderers[0]
    else:
        # Assume we have a single renderer.
        sample = renderers
    for cds_filter in sample.view.filters:
        # Sync filter to widget.
        cds_filter.group = widget.value
    # Sync groupfilters to widget (for multi-lines?).
    link_widgets_to_groupfilters(widget,
                                 source=sample.data_source, 
                                 view=sample.view)

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

if __name__ == "__main__":
    # Running from command line.    
    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)
    
    title = "tscomp: " + Path(args.datafile).stem
    
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
