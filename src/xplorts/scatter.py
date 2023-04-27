#!/usr/bin/env python
# coding: utf-8
"""
Make standalone interactive marker charts for categorical data.

Can be imported as a module, or run from the command line as a Python script.

When imported as a module, the function `grouped_scatter()` is defined.

When run from the command line, `scatter.py` reads data from a `csv` file and
creates an HTML document that displays an interactive line chart.
    
    In the `csv` file, the first row of data defines column names.  
    The file should include:
        - a column of independent variable categories, 
        - a column of category names for a split factor, and 
        - one or more columns of data values to be plotted as markers
          against the independent variable.  
    
    An interactive chart is created, with widgets to select one of the split
    factor category names (from a pulldown list or a slider), and a chart with
    one series of markers for each value column.  The independent variable is
    plotted against either the x or y axis.


Command line interface
----------------------
usage: scatter.py [-h] [-b BY] [-x X | -y Y] [-m MARKER]
                  [-v VALUES [VALUES ...]] [-g ARGS] [-t SAVE] [-s]
                  datafile

Create interactive scatter plot for data series with a split factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Factor variable for splits
  -x X                  Independent variable, for horizontal axis
  -y Y                  Independent variable, for vertical axis
  -m MARKER, --marker MARKER
                        Shape to use for markers. Passed to Bokeh
                        `Figure.scatter()`.
  -v VALUES [VALUES ...], --values VALUES [VALUES ...]
                        Dependent variables to plot against independent
                        variable
  -g ARGS, --args ARGS  Keyword arguments for grouped_stack(), specified as
                        YAML mapping
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -s, --show            Show interactive .html


Application program interface (API)
-----------------------------------
grouped_scatter
    Add a scatter plot to a figure, with legend entry and hover tooltip.
"""

#%%

from bokeh.io import save, show
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Div

import argparse
import pandas as pd
from pathlib import Path
import yaml

## Imports from this package
from base import (add_hover_tool, extend_legend_items, factor_view, 
                  filter_widget, iv_dv_figure, 
                  link_widgets_to_groupfilters, set_output_file, variables_cmap)
from slideselect import SlideSelect

#%%

def grouped_scatter(
    fig,
    iv_axis="x",  # axis for independent variable.
    iv_variable=None,
    marker_variable=None,
    marker="circle",
    tooltips=[],  # optional
    **kwargs  # Usually need `source` and `view` among these.
):
    """
    Add a scatter plot to a figure, with legend entry and hover tooltip
    
    Parameters
    ----------
    fig : Bokeh Figure
        A scatter glyph will be added to this figure.
    iv_axis : str, default "x"
        Either "x" or "y".  Defines the chart orientation, with a categorical independent 
        variable plotted along either the horizontal "x" axis, or the vertical "y" axis.
    iv_variable : str
        Name of data source column to plot along the `iv_axis`.
    marker_variable : str
        Dependent variable to plot against `iv_variable`.
    marker : str, default "circle"
        Shape to use for markers.  Passed to `Figure.scatter()`.
    tooltips : list
        Optional additional tooltips.
    kwargs : mapping
        Passed to `bokeh.plotting.figure.scatter()`.  Should normally map "source" to a
        `ColumnDataSource` and "view" to a `GroupView` object to achieve a chart
        that shows one level of a split factor at a time.
        
    Returns
    -------
    Bokeh renderer
    
    Examples
    --------
    from slideselect import SlideSelect

    ## Define a growth series, split by industry.
    df_growth = pd.DataFrame([
        (2001, 'A', 10),
        (2002, 'A', 5),
        (2003, 'A', -2),
        (2001, 'B', 3),
        (2002, 'B', 7),
        (2003, 'B', 4)
    ], columns=["date", "industry", "jobs"])
    source = ColumnDataSource(df_growth)

    # Make a widget to choose an industry to show.
    factor_levels = sorted(df_growth["industry"].unique())
    filter_widget = SlideSelect(options=factor_levels,
                                name="industry_filter")

    # Link the widget to a view showing one industry at a time.
    view_by_factor = factor_view(source, "industry")
    link_widgets_to_groupfilters(filter_widget, 
                                 view=view_by_factor)
    color_map = {"jobs": "chocolate"}
    fig = iv_dv_figure(
        iv_data = source.data["date"],
        iv_axis = "x",
    )

    vbars = grouped_scatter(fig, iv_axis="x", iv_variable="date", marker_variable="gva",
                            color_map=color_map, source=source, view=view_by_factor)

    # Show widget and chart.
    show(layout(
        [[filter_widget],
         [fig]])
    """

    assert iv_axis in "xy", f"iv_axis should be 'x' or 'y', not {iv_axis}"
    dv_axis = "xy".replace(iv_axis, "")  # axis for dependent variable.
    dv_direction = "vertical" if iv_axis == "x" else "horizontal"

    if marker_variable in ("", []):
        # Return empty list of renderers.
        return []
    
    # Make scatter.
    scatter_defaults = {
        "size": 6,
        "alpha": 0.6,
        "hover_fill_alpha": 1.0,  # Highlight hovered marker.
    }
    markers = fig.scatter(
        **{
            iv_axis: iv_variable,
            dv_axis: marker_variable
        },
        name=marker_variable,
        marker=marker,
        **{**scatter_defaults, **kwargs}  # kwargs can override these defaults.
    )

    extend_legend_items(
        fig,
        {marker_variable: markers}
    )

    ## Define hover info for markers.
    # Show name of hovered variable, along with date and the value.
    tooltip = '$name @date: @$name{0,0.0}'
    
    add_hover_tool(fig, [markers], ("marker", tooltip), *tooltips)

    return markers


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
        description="Create interactive scatter plot for data series with a split factor"
    )
    parser.add_argument("datafile", 
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    iv_group = parser.add_mutually_exclusive_group()
    iv_group.add_argument("-x", type=str,
                          help="Independent variable, for horizontal axis")
    iv_group.add_argument("-y", type=str,
                          help="Independent variable, for vertical axis")

    parser.add_argument("-m", "--marker", type=str,
                        help="Shape to use for markers.  Passed to Bokeh `Figure.scatter()`.")

    parser.add_argument("-v", "--values", 
                        nargs="+", type=str,
                        help="Dependent variables to plot against independent variable")
    
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for grouped_scatter(), specified as YAML mapping")

    parser.add_argument("-t", "--save", type=str, 
                        help="Name of interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true", 
                        help="Show interactive .html")
    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for grouped_multi_lines().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)

#%%
def main():
    """
    Parse command line arguments and make a scatter chart
    """
    
    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)
    
    # Unpack args specifying which columns to use.
    if all(getattr(args, arg) is None for arg in ["x", "y", "by", "values"]):
        # Get datevar from first column, byvar from second, values from remaining.
        iv_axis = "x"
        iv_variable, byvar = data.columns[:2]
        datavars = data.columns[2:]
    else:
        # Get byvar and datavars from explicit arguments, and optionally datevar too.
        byvar = args.by
        datavars = args.values
        if args.x is not None:
            iv_axis = "x"
            iv_variable = args.x
        else:
            iv_axis = "y"
            iv_variable = args.y
            
    marker = args.marker or "circle"
    
    title = "scatter: " + Path(args.datafile).stem
    
    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )
    
    # Convert str to float so we can plot the data.
    data[datavars] = data[datavars].astype(float)
    
    # Make a slide-select widget to choose factor level.
    widget = SlideSelect(options=list(data[byvar].unique()),
                         name=byvar + "_select")

    source = ColumnDataSource(data)
    view_by_factor = factor_view(source, byvar)

    link_widgets_to_groupfilters(widget, 
                                 view=view_by_factor)
    
    # Map variables to colors.
    default_color_map = variables_cmap(datavars,
                                       "Category10_10")

    # Labels for axis.
    iv_data = data[iv_variable].unique()
    iv_data = reversed(iv_data) if iv_axis == "y" else list(iv_data)

    fig = iv_dv_figure(
        iv_data = iv_data,
        iv_axis = iv_axis,
    )

    # Make chart, and link widget to make one set of bars visible.
    for var in datavars:
        glyph = grouped_scatter(
            fig,
            iv_axis=iv_axis,
            iv_variable=iv_variable,
            marker_variable=var,
            marker=marker,
            source=source,
            view=view_by_factor,
            color=default_color_map[var],
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

    
if __name__ == "__main__":
    main()

#%% Move to test
    
if False:
    df_data = pd.DataFrame([
        (2001, 'A', 100, 100),
        (2002, 'A', 105, 102),
        (2003, 'A', 110, 105),

        (2001, 'B', 100, 100),
        (2002, 'B', 90, 102),
        (2003, 'B', 95, 98)
    ], columns=["date", "industry", "gva", "hours worked"])
    df_data["oph"] = 100 * df_data["gva"] / df_data["hours worked"]
    df_data["periodicity"] = "annual"

    # Make standard date variables.
    df_data["date"] = pd.to_datetime(df_data["date"].astype(str)).dt.to_period("A")
    df_data["year"] = df_data["date"].dt.year
    df_data["quarter"] = df_data["date"].dt.quarter

    # Cumulative growth.
    df_data.sort_values(["industry", "date"], inplace=True)

    data_variables = ["oph", "gva", "hours worked"]
    sign_reverse_variables = ["hours worked"]

    # Calculate offset for type of growth (QoQ, QoA, QoYYYY, etc.).
    df_growth = df_data.copy().reset_index(drop=True)
    df_growth["growth_offset"] = pd.to_datetime("2001").year - df_growth["date"].dt.year

    # Apply offset to data variables to calculate growths.
    baseline_index = df_growth.index + df_growth["growth_offset"]
    baseline = df_growth[data_variables].iloc[baseline_index, :].reset_index(drop=True)
    df_growth[data_variables] = (df_growth[data_variables] / baseline - 1) * 100
    
    # Reverse sign where relevant.
    df_growth[sign_reverse_variables] *= -1
    sign_reverse_map = {name: name + " (sign reversed)" for name in sign_reverse_variables}
    df_growth.rename(columns=sign_reverse_map, inplace=True)
    growth_variables = [sign_reverse_map.get(name, name) for name in data_variables]
        
    factor = "industry"
    factor_levels = sorted(df_data[factor].unique())

    #dates = sorted(df_data["date"].unique())

    ##df_growth.to_csv("oph_gva_hours_growth_by_ab.csv")


# In[ ]:


if False:
    df_growth["year"] = df_growth["year"].astype(str)
    df_growth["year"]

    (line_var, *bar_vars) = growth_variables

    filter_widget = SlideSelect(options=factor_levels,
                                name=factor + "_filter")  # Show this in a layout.

    fig = grouped_stack(
        df_growth,
        bar_vars,
        x="year",
        by=factor,
        widget=filter_widget,
        color_map={},
        palette=None,
        fig=None,
        fig_options={}
    )


    hbars = grouped_stack(
        df_growth,
        bar_vars,
        y="year",
        by="industry",
        reverse=True,
        widget=filter_widget,
        color_map={},
        palette=None,
        fig=None,
        fig_options={}
    )

    

    # Make app that shows widget and chart.
    app = layout([
        [filter_widget],
        [fig, hbars]
    ])

    show(app)

