#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
Make standalone interactive line charts for time series data

When imported as a module, the function `grouped_multi_lines()` is
defined.

When run from the command line, the function `grouped_multi_lines()`
is run.

`grouped_multi_lines()` reads data from a `csv` file.  The first row 
of data defines column names.  The file should include:
    - a column of dates (annual, quarterly or monthly), 
    - a column of category names, and 
    - one or more columns of data values to be plotted against dates.  

An interactive chart is created, with widgets to select one of the
category names (from a pulldown list or a slider), and a chart with
one line for each value column.  Dates are plotted along the horizontal
axis.

The interactive chart can be viewed immediately in a web browser or can
be saved as a standalone `html` file.  The interactive `html` file requires 
a web browser to view, but does not need an active internet connection and 
can be viewed offline.  Once created, the `html` file does not require Python,
so it is easy to share the interactive chart.

Command line interface
----------------------
usage: grouped_multi_lines.py [-h] [-b BY] [-d DATEVAR] [-l LINES [LINES ...]]
                              [-g ARGS] [-p PALETTE] [-t SAVE | -T] [-s]
                              datafile

Create interactive charts for time series data split by a factor

positional arguments:
  datafile              Name of .csv file with time series data split by a
                        factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Name of factor variable
  -d DATEVAR, --datevar DATEVAR
                        Name of date variable
  -l LINES [LINES ...], --lines LINES [LINES ...]
                        Variables to show as time series lines
  -g ARGS, --args ARGS  Keyword arguments for grouped_multi_lines()
  -p PALETTE, --palette PALETTE
                        Name of color palette from bokeh.palettes
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -T, --nosave          Do not save interactive .html
  -s, --show            Show interactive .html after save

Application program interface (API)
-----------------------------------
grouped_multi_lines(data, data_variables, date_variable="date",
                    by=None, widget=None, color_map={}, palette=None,
                    line_style_map={}, fig=None, fig_options=None)
    Make an interactive Bokeh `figure` showing multi_line time series 
    charts for a set of factor levels.

link_widget_to_lines(widget, renderers)
    Attach a callback to a select widget, to update the `visible` property
    of an array of Bokeh renderers when the selection changes.
"""
None


# In[34]:


from bokeh import palettes
from bokeh.io import output_file, output_notebook, save, show
from bokeh.layouts import gridplot, layout
from bokeh.models import (ColumnDataSource, CustomJS, CustomJSHover, HoverTool, Legend, LegendItem)
from bokeh.plotting import figure

import argparse
import pandas as pd
import re
import warnings
import yaml

from collections import defaultdict
from functools import partial
from itertools import zip_longest
from pandas.core.groupby.generic import DataFrameGroupBy
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from pathlib import Path

## Find slideselect module near current working directory.
#from sys import path as syspath
#import_folder = (Path.cwd() / "../Chart_browser").as_posix()
#if import_folder not in syspath:
#    syspath.append(import_folder)
from base import (add_hover_tool, date_tuples, extend_legend_items, iv_dv_figure, 
                  link_widgets_to_groupfilters, set_output_file, unpack_data_varnames, 
                  variables_cmap)
from slideselect import SlideSelect


# In[ ]:


def link_widget_to_lines(widget, renderers):
    """
    Attach callback to selection widget, to update visibility of renderers
    
    The JS callback is triggered by changes to the `value` property of
    the widget.  When triggered, the callback hides the current renderer
    and unhides the renderer indexed by the new value of the widget.
    
    The first time it is triggered the callback hides the first renderer.
    To work correctly with a different initial visible renderer other than
    renderers[0], set the `.option_index` property of the widget to the 
    index of the initial visible renderer.
    
    Parameters
    ----------
    widget: Bokeh widget or layout
        May be an object with a `value` attribute and a method `js_on_change()`,
        like a Bokeh widget.  Alternatively, may be an object with a `handle` 
        attribute which is itself an object with a `value` attribute and a method
        `js_on_change()`, like a `SlideSelect` layout of two widgets.
    
    renderers: list
        List of Bokeh renderers, typically from the `renderers` property of a
        Bokeh `figure`.  The callback will set the `visible` property of individual
        renderers to hide the currently visible one and unhide the one selected
        by the new value of `widget`.
    """
    # Get widget handle (e.g. for SlideSelect), else link directly to widget.
    filter_handle = getattr(widget, "handle", widget)

    filter_handle.js_on_change(
        'value',
        CustomJS(
            args={"glyphs": renderers},
            code="""
                console.log('> JS callback');
                const option_index = this.options.indexOf(this.value);

                if (!("recent_index" in this))
                    this.previous_index = 0;  // Assume first glyph might be visible.
                else if (option_index != this.recent_index)
                    this.previous_index = this.recent_index;
                                
                // Hide currently visible glyph.
                glyphs[this.previous_index].visible = false;
                console.log('Made glyph ' + this.option_index + ' INvisible');

                // Show glyph currently selected by widget.
                glyphs[option_index].visible = true;
                console.log('Made glyph ' + option_index + ' visible');
                
                // Save current option_index to check next time.
                this.recent_index = option_index;
            """
        ))


# In[4]:



# Flexible formatter to pick one value out of a list (as for
# multi_line `xs` or `ys`).  Safe to use on scalar values too.
hover_segment_value = CustomJSHover(
    code="""
        console.log("> hover_segment_value", value);
        if (Array.isArray(value))
            // Index into value with segment_index (e.g. for multi-line).
            var result = value[special_vars["segment_index"]];
        else
            // Use (scalar?) value directly.
            result = value;
        return "" + result;
    """)


# In[60]:


class MultilineDataBuilder():
    """
    Maps names of columns to lists of lists, or sequences or arrays
    
    A class with helper methods to build 
    columns appropriate for `multi_line` glyphs.
    
    Methods
    -------
    
    """
    
    data = pd.DataFrame()
    
    def __init__(self, xs, data_variables=None, iv_variable=None, hover_data=None,
                 options={}, **kwargs):
    
        if iv_variable is None:
            iv_variable = xs.name
        xs = list(xs)
        
        if data_variables is None:
            if kwargs == {}:
                raise ValueError("missing data_variables")
            # Use (first) kwarg as column name for list of variable names.
            index_name, data_variables = kwargs.pop(next(iter(kwargs)))
            
            # Give warning about excess kwargs.
            if len(kwargs):
                warnings.warn(f"extra keywords ignored: {kwargs.keys()}")
        else:
            # Define default name for column of variable names.
            index_name = "variable"

        # Start dataframe with one row per variable.
        index = pd.Index(data_variables, name=index_name)
        self.data = pd.DataFrame(index=index)

        # Use same independent axis for each variable.
        self.fill_column(iv_variable, xs)
        
        if hover_data is not None:
            # Use same IV axis hover data for each variable.
            self.fill_column(hover_data.name, list(hover_data))
        
        self.options(options)
        
    def fill_column(self, column, value):
        """
        Assign the same value to each row
        """
        
        self.data[column] = [value] * len(self.data.index)
    
    def set_column(self, column, values):
        """
        Assign values to corresponding rows of a column
        
        Values can be a scalar, a list with one value per row,
        a Series, or a mapping.
        """
        
        # Coerce setting to Series compatible with .data.
        #  - Scalar will broadcast to fill column.
        #  - List must be same length as .data.index.
        #  - Mapping or series will use keys to match index.
        s = pd.Series(values, index=self.data.index)
        self.data[column] = s

    def options(self, *args, **kwargs):
        """
        Set columns with per-variable values
        """
        
        if len(args):
            assert len(args) == 1, "expected at most one positional argument"
            assert isinstance(args[0], dict), "positional argument should be a mapping"
            # Use positional argument as mapping, overriden by any kwargs.
            kwargs = {**(args[0]), **kwargs}

        for option_name, setting in kwargs.items():
            self.set_column(option_name, setting)

    @property
    def as_cds(self):
        """
        Coerce data to ColumnDataSource suitable for multi_line()
        """
        
        # Coerce to dict of dict; {column: {row: value, ...}, ...}.
        dod = self.data.reset_index().to_dict()
        # Collapse to dict of lists; {column: [value, ...], ...}.
        dol = {column: list(d.values()) for column, d in dod.items()}
        return ColumnDataSource(dol)
        


# In[63]:


def grouped_multi_lines(
    fig,
    data,
    iv_variable,
    data_variables,
    by = None,
    cds_options={},
    tooltips=[],  # optional
    **kwargs):
    """
    Multi_line chart overlays for a set of factor levels
    
    Creates a Bokeh `figure` with one `multi_line` glyph for each unique value of 
    `by`.  Dates are plotted along the horizontal axis.  The first `multi_line`
    is initially visible and the rest are hidden by setting their `visible`
    property to `False`.
    
    Parameters
    ----------
    data: DataFrame, DataFrameGroupBy
        Data columns must include a date variable, a categorical factor variable,
        and one or more value variables.
    data_variables: list
        Names of data columns.  The chart will show a line for each data
        variable.
    iv_variable: str or dict
        If str, the name of a data column, which will be shown on the horizontal
        axis.  
        
        If dict, should map key "plot" to a variable to show on the
        horizontal axis and should map key "hover" to a corresponding variable
        to display in hover information.  This is often useful when displaying
        quarterly dates as nested categories like `("2020", "Q1")`.
    by: str, default None
        Name of a categorical factor variable.  Required if `data` is a 
        `DataFrame`, ignored if `data` is a `DataFrameGroupBy` object.  
        A multi_line glyph will be created for each unique value of the
        `by` variable.
    widget: Bokeh widget or layout, default None
        If given, `widget` will be linked to the `multi_line` charts to show
        only one set of lines at a time.  The values of `widget` should span
        the range from zero to one less than the number of unique values of
        the `by` variable.
    color_map: dict, default {}
        Maps some or all data variables to colors, to override default colors  
        from `palette`.
    palette: Array of colors, optional
        If not given, Bokeh `Category10_10` colors are used.  Either way, 
        colors are recycled if there are more data variables than colors in 
        the palette.
    line_style_map: dict, default {}
        Maps some or all data variables to line styles like 'solid' or 'dashed',
        and so forth.  If not given, lines are solid.
    """
    
    if data_variables in (None, []):
        # Return empty list of renderers.
        return []
    
    # Wrap single data variable in list if necessary.
    if isinstance(data_variables, str):
        data_variables = [data_variables]
    
    if isinstance(data, DataFrameGroupBy):
        grouped = data
    else:
        # Group data, preserving order of `by`.
        grouped = data.groupby(by=by, sort=False)
    
    if isinstance(iv_variable, dict):
        iv_plot_variable = iv_variable["plot"]
        iv_hover_variable = iv_variable["hover"]
    else:
        iv_plot_variable = iv_hover_variable = iv_variable
    
    # Make template multi_line_data based on first group.
    _, df0 = next(iter(grouped))
    mldata = MultilineDataBuilder(
        df0[iv_plot_variable],
        data_variables,
        hover_data = (df0[iv_hover_variable] if iv_hover_variable != iv_plot_variable
                      else None),
        options=cds_options
    )

    # Add multi_line glyphs to figure, for each factor level.
    next_renderer_idx = len(fig.renderers)
    for group_name, group_df in grouped:
        # Make list of data values for each variable.
        mldata.set_column(
            "value",
            [list(group_df[var]) for var in data_variables]
        )
        mldata.set_column("group", group_name)

        fig.multi_line(
            xs=iv_plot_variable, 
            ys="value",
            name="lines_" + group_name,
            source=mldata.as_cds,
            visible=False,
            **kwargs
        )
        
    lines = fig.renderers[next_renderer_idx:]

    # Show first set of lines.
    first_multi_line = lines[0]
    first_multi_line.visible = True

    # Add to legend.
    new_legend_items = [
            # Include legend item for each variable,
            #  using styles from the first multi_line renderer.
            LegendItem(label=var, 
                       renderers=[first_multi_line], 
                       index=i
                      ) \
            for i, var in enumerate(data_variables)
    ]
    extend_legend_items(
        fig,
        items=new_legend_items,
    )
    
    
    ## Define hover info for lines.
    # Show name of hovered glyph, along with hover-date and the value.
    lines_tooltip = f"@variable @{iv_hover_variable}{{custom}}: $data_y{{0,0.0}}"
    add_hover_tool(fig, lines, 
                   ("line", lines_tooltip), 
                   (by if by is not None else "group", "@group"),
                   *tooltips,
                   attachment="vertical",
                   formatters={f'@{iv_hover_variable}': hover_segment_value},
                   name="Hover lines",
                   description="Hover lines",
                  )

    return(lines)


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
        description="Create interactive line charts for time series data with a split factor"
    )
    parser.add_argument("datafile", 
                        help="Name of .csv file with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Name of factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Name of date variable")
    parser.add_argument("-l", "--lines", 
                        nargs="+", type=str,
                        help="Variables to show as time series lines")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for grouped_multi_lines()")

    parser.add_argument("-t", "--save", type=str, 
                        help="Name of interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true", 
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for grouped_multi_lines().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)


# In[ ]:


if __name__ == "__main__":
    # Suppress quarterly or monthly axis labels for time series longer than this.
    DATE_THRESHOLD = 40
    
    args = _parse_args()

    data = pd.read_csv(args.datafile, dtype=str)
    
    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "lines"],
        data.columns)
    datavars = varnames["lines"]
    
    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = ", ".join(datavars) + " by " + varnames["by"]
    )
    
    # Make a slide-select widget to choose industry.
    byvar = varnames["by"]
    widget = SlideSelect(options=list(data[byvar].unique()),
                         name=byvar + "_select")
    
    # Transform monthly and quarterly dates to nested categories.
    datevar = varnames["date"]
    data = data.assign(**{datevar: date_tuples(data[datevar],
                                               length_threshold=DATE_THRESHOLD)})

    # Prepare to suppress most quarters or months on axis if lots of them.
    suppress_factors = (isinstance(data[datevar][0], tuple)
                        and len(data[datevar].unique()) > 40)

    fig = iv_dv_figure(
        iv_axis = "x",
        iv_data = data[datevar],
        suppress_factors = suppress_factors,
    )
    
    default_color_map = variables_cmap(datavars[::-1],
                                       "Category20_20")
    default_line_colors = [default_color_map[var] for var in datavars]
    
    default_line_dash = ["solid"] * len(datavars)
    default_line_dash[1::2] = ["dashed"] * len(datavars[1::2])
    
    default_args = dict(
        line_alpha=0.8,
        hover_line_alpha=1,
        line_width=2,
        hover_line_width=4,
        cds_options=dict(color=default_line_colors,
                         line_dash=default_line_dash),
        color="color",
        line_dash="line_dash",
    )
    
    lines = grouped_multi_lines(
        fig,
        data,
        iv_variable=datevar,
        data_variables=datavars,
        by=varnames["by"],
        **{**default_args, **args.args},
    )

    link_widget_to_lines(widget, lines)

    # Make app that shows widget and chart.
    app = layout([
        [widget],
        [fig]
    ])
    
    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.


# In[ ]:


if False: #__name__ == "__main__":
    # Make a test chart to show in Jupyter.
    df_data = pd.DataFrame.from_records([
        dict(date=2001, industry='A', gva_idx=100, hours_idx=100),
        dict(date=2002, industry='A', gva_idx=105, hours_idx=102),
        dict(date=2003, industry='A', gva_idx=110, hours_idx=105),
        dict(date=2001, industry='B', gva_idx=100, hours_idx=100),
        dict(date=2002, industry='B', gva_idx=90, hours_idx=102),
        dict(date=2003, industry='B', gva_idx=95, hours_idx=98)
    ])
    df_data["oph_idx"] = 100 * df_data["gva_idx"] / df_data["hours_idx"]
    df_data["periodicity"] = "annual"

    # Make standard date variables.
    df_data["date"] = pd.to_datetime(df_data["date"].astype(str)).dt.to_period("A")
    df_data["year"] = df_data["date"].dt.year
    df_data["quarter"] = df_data["date"].dt.quarter
    
    # Make a slide-select widget to choose industry.
    widget = SlideSelect(options=list(df_data["industry"].unique()),
                         name="industry_select")
    
    fig = grouped_multi_lines(df_data, 
                              data_variables=["oph_idx", "gva_idx", "hours_idx"],
                              palette=palettes.Category20_3[::-1],
                              by="industry",
                              line_style_map={"hours_idx": "dashed"},
                              widget=widget)
    
    output_notebook()
    app = layout([
        [widget],
        [fig]
    ])

    show(app)


# In[ ]:




