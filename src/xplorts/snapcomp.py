#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
Interactive chart showing snapshot components and total by split category
"""


# In[1]:


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
from scatter import grouped_scatter
from slideselect import SlideSelect
from stacks import grouped_stack


# In[ ]:


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


# In[ ]:


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
    link_widgets_to_groupfilters(widget,
                                 source=sample.data_source, 
                                 view=sample.view)


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
        description="Create interactive horizontal bar chart for snapshot components with a split factor"
    )
    parser.add_argument("datafile", 
                        help="Name of .csv file with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Name of factor variable for splits")

    parser.add_argument("-y", "--iv", type=str,
                        help="Name of independent variable on vertical axis")

    parser.add_argument("-m", "--markers", type=str,
                        help="Variable to show as marker points")
    parser.add_argument("-x", "--bars", 
                        nargs="+", type=str,
                        help="Variables to show as horizontal stacked bars")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for components_figure()")

    parser.add_argument("-L", "--last", action="store_true", 
                        help="Initial chart shows last level of `by` variable")

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
    if all(getattr(args, arg) is None for arg in ["iv", "by", "markers", "bars"]):
        # Get y from first column, byvar from second, markers from third, datavars from remaining.
        y, byvar, linevar = data.columns[:3]
        datavars = data.columns[3:]
    else:
        # Get byvar, linevar and datavars from explicit arguments, and optionally datevar too.
        byvar = args.by
        markervar = args.markers
        datavars = args.bars
        y = args.iv
    
    # Convert str to float so we can plot the data.
    data[markervar] = data[markervar].astype(float)
    
    # Configure output file for interactive html.
    outfile = args.save
    if outfile is None:
        # Use datafile name, with .html extension.
        outfile = Path(args.datafile).with_suffix(".html").as_posix()
    title = ", ".join(datavars) + " by " + byvar
    output_file(outfile, title=title, mode='inline')
    
    dependent_variables = datavars.copy()
    if markervar is not None:
        dependent_variables.insert(0, markervar)

    default_color_map = variables_cmap(dependent_variables[::-1],
                                       palettes.Category20_20)
    default_bar_colors = [default_color_map[var] for var in datavars]
    
    # Make a slide-select widget to choose factor level.
    widget = SlideSelect(options=list(data[byvar].unique()),
                         title=byvar,  # Shown.
                         name=byvar + "_select")

    fig = iv_dv_figure(
        iv_data = data[y].unique(),
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
        by=byvar,
        marker_variable=markervar,
        y=y,
        bar_variables=datavars,
        scatter_args=scatter_args,
        bar_args=bar_args,
        **args.args)

    if args.last:
        widget.value = widget.options[-1]
    link_widget_to_snapcomp_figure(widget, fig)

    # Make app that shows widget and chart.
    app = layout([
        [widget],
        [fig]
    ])
    
    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

