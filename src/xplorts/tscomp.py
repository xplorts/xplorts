#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
Interactive chart showing time series components and total by split category
"""


# In[3]:


from bokeh.layouts import gridplot, layout
from bokeh.io import output_file, save, show
from bokeh.models import ColumnDataSource
from bokeh import palettes

import argparse
from pathlib import Path
import pandas as pd
import re
import yaml

from base import add_hover_tool, factor_view, iv_dv_figure, link_widgets_to_groupfilters, variables_cmap
from lines import grouped_multi_lines, link_widget_to_lines
from slideselect import SlideSelect
from stacks import grouped_stack


# In[ ]:


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


# In[ ]:


def link_widget_to_tscomp_figure(widget, fig=None, lines=None, bars=None):
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


# In[ ]:


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
        description="Create interactive time series chart for components with a split factor"
    )
    parser.add_argument("datafile", 
                        help="Name of .csv file with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Name of factor variable for splits")

    parser.add_argument("-x", "--datevar", type=str,
                        help="Name of date variable")

    parser.add_argument("-l", "--line", type=str,
                        help="Variable to show as time series line")
    parser.add_argument("-y", "--bars", 
                        nargs="+", type=str,
                        help="Variables to show as stacked bars")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for ts_components_figure()")

    parser.add_argument("-t", "--save", type=str, 
                        help="Name of interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true", 
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for ts_components_figure().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)


# In[ ]:


if __name__ == "__main__":
    # Running from command line (or in Notebook?).
    
    args = _parse_args()
    print(args)

    data = pd.read_csv(args.datafile, dtype=str)
    
    # Unpack args specifying which columns to use.
    if all(getattr(args, arg) is None for arg in ["datevar", "by", "line", "bars"]):
        # Get datevar from first column, byvar from second, line from third, datavars from remaining.
        datevar, byvar, linevar = data.columns[:3]
        datavars = data.columns[3:]
    else:
        # Get byvar, linevar and datavars from explicit arguments, and optionally datevar too.
        byvar = args.by
        linevar = args.line
        datavars = args.bars
        datevar = args.datevar or "date"
    
    # Configure output file for interactive html.
    outfile = args.save
    if outfile is None:
        # Use datafile name, with .html extension.
        outfile = Path(args.datafile).with_suffix(".html").as_posix()
    title = ", ".join(datavars) + " by " + byvar
    output_file(outfile, title=title, mode='inline')
    
    # Make a slide-select widget to choose factor level.
    widget = SlideSelect(options=list(data[byvar].unique()),
                         title=byvar,  # Shown.
                         name=byvar + "_select")
    
    # Map variables to colors.
    dependent_variables = datavars.copy()
    if linevar is not None:
        dependent_variables.insert(0, linevar)

    default_color_map = variables_cmap(dependent_variables[::-1],
                               palettes.Category20_20)
    default_bar_colors = [default_color_map[var] for var in datavars]

    fig = iv_dv_figure(
        iv_data = data[datevar].unique(),
        iv_axis = "x",
    )
    
    if linevar is None:
        line_args = {}
    else:
        # Use specified scatter_args, else defaults.
        line_args = args.args.pop(
            "line_args",
            {"color": default_color_map[linevar]})
        
    # Use specified bar_args, else defaults.
    bar_args = args.args.pop(
        "bar_args",
        {"color": default_bar_colors})

    # Make chart, and link widget to make one factor level visible.
    ts_components_figure(
        fig,
        data,
        by=byvar,
        line_variable=linevar,
        date_variable=datevar,
        bar_variables=datavars,
        line_args=line_args,
        bar_args=bar_args,
        **args.args)

    link_widget_to_components_figure(widget, fig)

    # Make app that shows widget and chart.
    app = layout([
        [widget],
        [fig]
    ])
    
    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

