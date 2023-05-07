#!/usr/bin/env python
# coding: utf-8
"""
Make standalone interactive line charts for time series data.

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, `lines.py` reads data from a `csv` file and
creates an HTML document that displays an interactive line chart.
      
    In the `csv` file, the first row of data defines column names.  
    The file should include:
        - a column of dates (annual, quarterly or monthly), 
        - a column of category names, and 
        - one or more columns of data values to be plotted against dates.  

    An interactive chart is created, with widgets to select one of the
    category names (from a pulldown list or a slider).  The chart shows
    one line for each value column, with dates plotted along the horizontal
    axis.


Command line interface
----------------------
usage: lines.py [-h] [-b BY] [-d DATEVAR] [-l LINES [LINES ...]]
                              [-g ARGS] [-p PALETTE] [-t SAVE | -T] [-s]
                              datafile

Create interactive charts for time series data split by a factor

positional arguments:
  datafile              Name of .csv file with time series data split by a
                        factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Name of factor variable
  -d DATE, --date DATE
                        Name of date variable
  -l LINES [LINES ...], --lines LINES [LINES ...]
                        Variables to show as time series lines
  -g ARGS, --args ARGS  Keyword arguments for grouped_multi_lines()
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -s, --show            Show interactive .html


Application program interface (API)
-----------------------------------
grouped_multi_lines
    Add a multi-line plot to a figure, with legend entries and hover tooltip.

link_widget_to_lines
    Arrange to update the `visible` property of renderers when a 
    selection changes.
"""

#%%
from bokeh import palettes
from bokeh.io import save, show
from bokeh.layouts import layout
from bokeh.models import (ColumnDataSource, CustomJS, CustomJSHover, LegendItem)
from bokeh.models.widgets import Div

import argparse
import pandas as pd
from pathlib import Path
import warnings
import yaml

from pandas.core.groupby.generic import DataFrameGroupBy

from xplorts.base import (add_hover_tool, extend_legend_items, 
                          filter_widget, iv_dv_figure, 
                          set_output_file, unpack_data_varnames, 
                          variables_cmap)
from xplorts.dutils import date_tuples
from xplorts.slideselect import SlideSelect


#%%

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



# Flexible formatter to pick one value out of a list (as for
# multi_line `xs` or `ys`).  Safe to use on scalar values too.
_hover_segment_value = CustomJSHover(
    code="""
        console.log("> _hover_segment_value", value);
        if (Array.isArray(value))
            // Index into value with segment_index (e.g. for multi-line).
            var result = value[special_vars["segment_index"]];
        else
            // Use (scalar?) value directly.
            result = value;
        return "" + result;
    """)


#%%

class _MultilineDataBuilder():
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
        

#%%

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
    Add multi_line chart overlays to a plot, for time series data with
    a set of factor levels.
    
    Adds to a Bokeh `figure`, one `multi_line` glyph for each unique value of 
    `by`, with legend entries and hover tooltip.
    
    Dates are plotted along the horizontal axis.  The first `multi_line`
    is initially visible and the rest are hidden by setting their `visible`
    property to `False`.
    
    Parameters
    ----------
    fig: Bokeh Figure
        Figure to add to.
    data: DataFrame, DataFrameGroupBy
        Data columns must include a date variable, a categorical factor variable,
        and one or more value variables.
    iv_variable: str or dict
        If str, the name of a data column, which will be shown on the horizontal
        axis.  
        
        If dict, should map key "plot" to a variable to show on the
        horizontal axis and should map key "hover" to a corresponding variable
        to display in hover information.  This is often useful when displaying
        quarterly dates as nested categories like `("2020", "Q1")`.
    data_variables: list
        Names of data columns.  The chart will show a line for each data
        variable.
    by: str, default None
        Name of a categorical factor variable.  Required if `data` is a 
        `DataFrame`, ignored if `data` is a `DataFrameGroupBy` object.  
        A multi_line glyph will be created for each unique value of the
        `by` variable.
    cds_options: dict, default {}
       Mapping from column names to lists, to specify plotting attributes
       for multi_lines.  Each list should have a value for each of the
       data_variables, in the same order.
    tool_tips: list, default []
        Pre-existing tooltips to add to the hover tool in addition to the
        default tooltips.
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
    mldata = _MultilineDataBuilder(
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
                   formatters={f'@{iv_hover_variable}': _hover_segment_value},
                   name="Hover lines",
                   description="Hover lines",
                  )

    return(lines)


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
        description="Create interactive line charts for time series data with a split factor"
    )
    parser.add_argument("datafile", 
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")
    parser.add_argument("-l", "--lines", 
                        nargs="+", type=str,
                        help="Variables to show as time series lines")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for grouped_multi_lines(), specified as YAML mapping")

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
    
    title = "lines: " + Path(args.datafile).stem
    
    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )
    
    # Convert str to float so we can plot the data.
    data[datavars] = data[datavars].astype(float)
    
    # Make a slide-select widget to choose industry.
    split_widget = filter_widget(data[varnames["by"]], title=varnames["by"])
     
    # Transform monthly and quarterly dates to nested categories.
    datevar = varnames["date"]
    data_local = data.copy()
    data_local["_date_factor"] = date_tuples(data_local[datevar],
                                             length_threshold=DATE_THRESHOLD)

    # Prepare to suppress most quarters or months on axis if lots of them.
    suppress_factors = (isinstance(data_local["_date_factor"][0], tuple)
                        and len(data_local["_date_factor"].unique()) > DATE_THRESHOLD)

    fig = iv_dv_figure(
        iv_axis = "x",
        iv_data = data_local["_date_factor"],
        suppress_factors = suppress_factors,
        y_axis_label = "Value"
    )
    
    default_color_map = variables_cmap(datavars,
                                       "Category20_20")
    default_line_colors = [default_color_map[var] for var in datavars]
    
    # Use dash for alternating line colors within each similar pair.
    default_line_dash = ["solid"] * len(datavars)
    default_line_dash[0:-1:2] = ["dashed"] * len(datavars[0:-1:2])
    
    default_args = dict(
        line_alpha=0.8,
        hover_line_alpha=1,
        line_width=2,
        hover_line_width=4,
        cds_options=dict(color=default_line_colors,
                         line_dash=default_line_dash),
        color="color",
        line_dash="line_dash"
    )
    
    lines = grouped_multi_lines(
        fig,
        data_local,
        iv_variable=dict(plot="_date_factor", hover=datevar),
        data_variables=datavars,
        by=varnames["by"],
        **{**default_args, **args.args}
    )

    link_widget_to_lines(split_widget, lines)

    # Make app that shows widget and chart.
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        [split_widget],
        [fig]
    ])
    
    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

    
if __name__ == "__main__":
    main()

#%% Move to test.
    
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
    
    app = layout([
        [widget],
        [fig]
    ])

    show(app)

