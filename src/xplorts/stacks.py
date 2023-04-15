#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
Make standalone interactive vertical bar charts for time series data

When imported as a module, the function `grouped_stack()` is
defined.

When run from the command line, `stacks` reads data from a `csv` file
and creates an interactive chart.

The `stacks` command reads data from a `csv` file.  The first row 
of data defines column names.  The file should include:
    - a column of dates (annual, quarterly or monthly), 
    - a column of category names for a split factor, and 
    - one or more columns of data values to be plotted as stacked bars
      against dates.  The data values can include a mix of positive and
      negative values.

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
usage: stacks.py [-h] [-b BY] [-x DATEVAR] [-y BARS [BARS ...]] [-g ARGS]
                 [-p PALETTE] [-t SAVE | -T] [-s]
                 datafile

Create interactive stacked bars for data series with a split factor

positional arguments:
  datafile              Name of .csv file with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Name of factor variable for splits
  -x DATEVAR, --datevar DATEVAR
                        Name of date variable
  -y BARS [BARS ...], --bars BARS [BARS ...]
                        Variables to show as stacked bars
  -g ARGS, --args ARGS  Keyword arguments for grouped_stack()
  -p PALETTE, --palette PALETTE
                        Name of color palette from bokeh.palettes
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -T, --nosave          Do not save interactive .html
  -s, --show            Show interactive .html

Application program interface (API)
-----------------------------------
grouped_stacks(data, data_variables, x="date",
                    by=None, widget=None, color_map={}, palette=None,
                    fig=None, fig_options={})
    Grouped renderers for stacked bar charts with data that may be positive or negative

link_widget_to_filter_group(widget, source, filt):
    Attach a callback to a select widget, to set a filter `group` and
    emit a source change to update charts using that source.
"""

## For command line interface, be sure to activate the relevant conda environment
# On Windows (see LProd system on how to do it all in one command):
#  activate python36_plus_hv2
# On Mac:
#   conda activate python36_plus_hv2
None


# In[2]:


from bokeh.plotting import figure

from bokeh.core.properties import expr
from bokeh.layouts import gridplot, layout
from bokeh.models import (CDSView, ColumnDataSource, CustomJS, CustomJSExpr,
                          CustomJSFilter, CustomJSTransform, 
                          FactorRange, GroupFilter, HoverTool,
                          Legend, LegendItem, Select)
from bokeh import palettes
from bokeh.io import output_file, save, show
from bokeh.transform import factor_cmap, stack

import argparse
from itertools import tee, zip_longest
import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from pathlib import Path
import re
import yaml

## Imports from this package
from base import (add_hover_tool, extend_legend_items, factor_view, GhostBokeh, iv_dv_figure, 
                  link_widgets_to_groupfilters, variables_cmap)
from slideselect import SlideSelect
#from grouped_multi_lines import grouped_multi_lines

try:
    from itertools import pairwise
except ImportError:
    # Define local pairwise(), since itertools is too old to have it.
    # https://docs.python.org/3/library/itertools.html#itertools.pairwise
    def pairwise(iterable):
        """
        Stand-in for itertools.pairwise()
        
        pairwise('ABCDEFG') --> AB BC CD DE EF FG.
        """
        
        a, b = tee(iterable)
        next(b, None)  # Remove first item of second sequence.
        return zip(a, b)  # Pairs until second sequence is exhausted.


# In[3]:


## Miscellaneous helpers that should probably migrate elsewhere.

def accumulate_list(items):
    """
    Initial subsequences of increasing length from list of items
    
    Generator of lists.
    
    Examples
    --------
    gen = accumulate_list([1, 2])
    list(gen)
    # [[], [1], [1, 2]]
    """
    for i in range(len(items) + 1):
        yield items[:i]

def quarter_difference(date, baseline):
    """Number of quarters between two dates"""
    return y4q(date) - y4q(baseline)

def y4q(date):
    """
    Convert years to quarter-years
    
    Useful for calculating the number of quarters between two dates.
    
    Example
    -------
    q1 = pd.to_datetime("2001Q3")
    q2 = pd.to_datetime("2002Q1")
    qdiff = y4q(q2) - y4q(q1)
    qdiff
    # 2
    """
    try:
        y = date.year
        q = date.quarter
    except AttributeError:
        # Use .dt accessors of Pandas.
        y = date.dt.year
        q = date.dt.quarter
    return 4*y + q


# In[4]:


class StackRectified(GhostBokeh, CustomJSExpr):
    """
    An expression for stacking data columns with values above or below a threshold 
    
    Useful for making stacked bar charts with data involving both positive and negative
    values.
    """
    
    # Javascript code to sum deviations above (or below) a threshold, across a
    # list of source fields.  Deviations below (or above) the threshold are
    # ignored.
    # 
    # Needs Python `format()` field `{comparator}` to be substituted
    # (e.g. by '>' or '<') to make valid JS code.
    #
    # Uses {{}} to protect JS brackets from Python .format().
    _code_template = """
        // Assume `this.data`.
        // Expect args: `fields`, `threshold`.
        console.log("> Entering {name}, fields:", fields, "threshold:", threshold);
        
        const data_length = this.data[Object.keys(this.data)[0]].length;
        const stacked_xs = new Array(data_length).fill(threshold);
        var field = "";
        var field_value = 0;
        for (var i = 0; i < data_length; i++) {{
            // Calculate stack at row `i` of `this.data`.
            for (var j = 0; j < fields.length; j++) {{
                // Add value for measure j.
                field = fields[j];
                if (field in this.data) {{
                    field_value = this.data[field][i];
                    if (field_value {comparator} threshold)
                        stacked_xs[i] += field_value - threshold;
                }} else
                  console.log("Unknown field ignored", field);
            }}
        }}
        return stacked_xs;
    """
    
    def __new__(cls, fields, min_value=None, max_value=None, **kwargs):
        # Use bokeh model for CustomJSExpr to generate javascript to display this object.
        obj = super().__new__(cls, fields, **kwargs)
        #obj.__qualified_model__ = "CustomJSExpr"
        return obj
    
    def __init__(self, fields,
                 min_value=0, max_value=None,
                 name=None,
                 **kwargs):
        if max_value is None:
            comparator = ">"
            threshold = min_value
        else:
            comparator = "<"
            threshold = max_value
        code = self._code_template.format(
            comparator=comparator,
            name=name
        )
        super().__init__(
            args=dict(fields=fields,
                      threshold=threshold),
            code=code,
            name=name,
            **kwargs
        )

## StackUp and StackDown mimic bokeh Stack, but for rectified stacks.

class StackUp(StackRectified):
    """
    A JS Expression for stacking data columns with values exceeding a threshold 
    
    Useful for making stacked bar charts with data involving both positive and negative
    values.
    """
    def __init__(self, fields,
                 min_value=0,
                 name=None,
                 **kwargs):
        if kwargs.get("max_value") is not None:
            raise ValueError(f"max_value not allowed for StackUp, was {kwargs[max_value]}")
        super().__init__(fields,
                         min_value=min_value,
                         name=name,
                         **kwargs)


class StackDown(StackRectified):
    """
    A JS Expression for stacking data columns with values below a threshold 
    
    Useful for making stacked bar charts with data involving both positive and negative
    values.
    """
    def __init__(self, fields,
                 max_value=0,
                 name=None,
                 **kwargs):
        if kwargs.get("min_value", 0) != 0:
            raise ValueError(f"min_value not allowed for StackDown, was {kwargs[min_value]}")
        super().__init__(fields,
                         max_value=max_value,
                         name=name,
                         **kwargs)


## stack_up() and stack_down() mimic bokeh stack(), but for rectified stacks.

def stack_up(*fields, min_value=0):
    ''' Create a ``DataSpec`` dict to generate a ``StackUp`` expression
    for a ``ColumnDataSource``.

    Examples:

        .. code-block:: python

            p.vbar(bottom=stack_up("gva", "jobs"), ...

        will generate a ``StackUp`` that sums positive values of ``"gva"`` and ``"jobs"``
        columns of a data source, and use those values as the ``bottom``
        coordinate for a ``VBar``.

    '''

    return expr(StackUp(fields=fields, min_value=min_value))

def stack_down(*fields, max_value=0):
    ''' Create a ``DataSpec`` dict to generate a ``StackDown`` expression
    for a ``ColumnDataSource``.

    Examples:

        .. code-block:: python

            p.vbar(bottom=stack_down("gva", "jobs"), ...

        will generate a ``StackDown`` that sums negative values of ``"gva"`` and ``"jobs"``
        columns of a data source, and use those values as the ``bottom``
        coordinate for a ``VBar``.

    '''

    return expr(StackDown(fields=fields, max_value=max_value))


# In[5]:



## Reverse engineered `double_stack`, as described for Bokeh `vbar_stack()`.

def double_stack(stackers, key1, key2, **kwargs):
    list_generator = accumulate_list(stackers)
    for i, shorter_longer in enumerate(pairwise(list_generator)):
        shorter_list, longer_list = shorter_longer
        # If a keyword value is a list or tuple, then each call will get one
        # value from the sequence.
        other_args = {key: val[i] if isinstance(val, (list, tuple)) else val                          for key, val in kwargs.items()
                     }
        yield {key1: shorter_list, 
               key2: longer_list,
               "name": longer_list[-1],
               **other_args}

def double_stack_updown(stackers, key1, key2, **kwargs):
    """
    Wrap double_stack()
    """
    for dstack in double_stack(stackers, key1, key2, **kwargs):
        for wrapper in (stack_up, stack_down):
            wrapped_keys = {
                key1: wrapper(*dstack[key1]),
                key2: wrapper(*dstack[key2])
            }
            dstack_wrapped = {**dstack, **wrapped_keys}
            yield dstack_wrapped


# In[6]:


# Derived from Bokeh Figure.hbar_stack().
# https://docs.bokeh.org/en/latest/_modules/bokeh/plotting/_figure.html#figure.hbar_stack
def hbar_stack_updown(fig, stackers, **kw):
    ''' Generate multiple ``HBar`` renderers for positive levels stacked bottom
    to top, and negative levels stacked bottom to top.

    Args:
        stackers (seq[str]) : a list of data source field names to stack
            successively for ``left`` and ``right`` bar coordinates.

            Additionally, the ``name`` of the renderer will be set to
            the value of each successive stacker (this is useful with the
            special hover variable ``$name``)

    Any additional keyword arguments are passed to each call to ``hbar``.
    If a keyword value is a list or tuple, then each call will get one
    value from the sequence.

    Returns:
        list[GlyphRenderer]

    Examples:

        Assuming a ``ColumnDataSource`` named ``source`` with columns
        *2016* and *2017*, then the following call to ``hbar_stack_updown`` will
        will create four ``HBar`` renderers that stack right and/or left:

        .. code-block:: python

            hbar_stack_updown(p, ['2016', '2017'], x=10, width=0.9, color=['blue', 'red'], source=source)

        This is equivalent to the following two separate calls:

        .. code-block:: python

            p.hbar(left=stack_up(),         right=stack_up('2016'),           x=10, width=0.9, color='blue', source=source, name='2016')
            p.hbar(left=stack_up('2016'),   right=stack_up('2016', '2017'),   x=10, width=0.9, color='red',  source=source, name='2017')
            p.hbar(left=stack_down(),       right=stack_down('2016'),         x=10, width=0.9, color='blue', source=source, name='2016')
            p.hbar(left=stack_down('2016'), right=stack_down('2016', '2017'), x=10, width=0.9, color='red',  source=source, name='2017')

    '''
    hbar_arg_list = double_stack_updown(stackers, "left", "right", **kw)
    result = [fig.hbar(**hbar_args) for hbar_args in hbar_arg_list]
    return result


# In[7]:


# Derived from Bokeh Figure.vbar_stack().
# https://docs.bokeh.org/en/latest/_modules/bokeh/plotting/_figure.html#figure.vbar_stack
def vbar_stack_updown(fig, stackers, **kw):
    ''' Generate multiple ``VBar`` renderers for positive levels stacked bottom
    to top, and negative levels stacked bottom to top.

    Args:
        stackers (seq[str]) : a list of data source field names to stack
            successively for ``bottom`` and ``top`` bar coordinates.

            Additionally, the ``name`` of the renderer will be set to
            the value of each successive stacker (this is useful with the
            special hover variable ``$name``)

    Any additional keyword arguments are passed to each call to ``vbar``.
    If a keyword value is a list or tuple, then each call will get one
    value from the sequence.

    Returns:
        list[GlyphRenderer]

    Examples:

        Assuming a ``ColumnDataSource`` named ``source`` with columns
        *2016* and *2017*, then the following call to ``vbar_stack_updown`` will
        will create four ``VBar`` renderers that stack up and/or down:

        .. code-block:: python

            vbar_stack_updown(p, ['2016', '2017'], x=10, width=0.9, color=['blue', 'red'], source=source)

        This is equivalent to the following two separate calls:

        .. code-block:: python

            p.vbar(bottom=stack_up(),       top=stack_up('2016'),         x=10, width=0.9, color='blue', source=source, name='2016')
            p.vbar(bottom=stack_up('2016'), top=stack_up('2016', '2017'), x=10, width=0.9, color='red',  source=source, name='2017')
            p.vbar(bottom=stack_down(),       top=stack_down('2016'),         x=10, width=0.9, color='blue', source=source, name='2016')
            p.vbar(bottom=stack_down('2016'), top=stack_down('2016', '2017'), x=10, width=0.9, color='red',  source=source, name='2017')

    '''
    vbar_arg_list = double_stack_updown(stackers, "bottom", "top", **kw)
    result = [fig.vbar(**vbar_args) for vbar_args in vbar_arg_list]
    return result


# In[8]:


def grouped_stack(
    fig,
    iv_axis="x",
    iv_variable=None,
    bar_variables=[],
    #tooltips=[],  # optional
    **kwargs  # Usually need `source` and `view` among these.
):
    """
    Grouped renderers for stacked bar charts with data that may be positive or negative
    
    Parameters
    ----------
    iv_variable: str or dict
        If str, the name of a data column, which will be shown on the horizontal
        axis.  
        
        If dict, should map key "plot" to a variable to show on the
        horizontal axis and should map key "hover" to a corresponding variable
        to display in hover information.  This is often useful when displaying
        quarterly dates as nested categories like `("2020", "Q1")`.    
    """

    assert iv_axis in "xy", f"iv_axis should be 'x' or 'y', not {iv_axis}"
    dv_axis = "xy".replace(iv_axis, "")
    bar_direction = "vbars" if iv_axis == "x" else "hbars"
    bar_width_key = "width" if bar_direction=="vbars" else "height"
    
    if isinstance(iv_variable, dict):
        iv_plot_variable = iv_variable["plot"]
        iv_hover_variable = iv_variable["hover"]
    else:
        iv_plot_variable = iv_hover_variable = iv_variable

    stack_function = vbar_stack_updown if bar_direction=="vbars" else hbar_stack_updown
    
    if bar_variables == []:
        # Return empty list of renderers.
        return []
    
    bars = stack_function(
        fig,
        bar_variables,
        alpha=0.25,
        ## hover_fill_alpha=0.5,  # Highlight hovered set of bars (broken).
        **{iv_axis: iv_plot_variable},  # x= or y=.
        **{bar_width_key: 0.9},  # width= or height=.
        **kwargs,  # Usually include `source` and `view`.
    )

    extend_legend_items(
        fig,
        {var: bars[2*i] for i, var in enumerate(bar_variables)}
    )

    ## Define hover info for individual bars.
    # Show name of hovered bar, along with IV value and the bar value.
    #bar_tooltip = f'$name @{iv_hover_variable}: @$name{{0,0.0}}'
    
    #bar_hover = add_hover_tool(fig, bars, 
    #                           ("bars", bar_tooltip), 
    #                           *tooltips,
    #                           name="Hover individual bars",
    #                           description="Hover individual bars")

    return bars


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
        description="Create interactive stacked bars for data series with a split factor"
    )
    parser.add_argument("datafile", 
                        help="Name of .csv file with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Name of factor variable for splits")


    iv_group = parser.add_mutually_exclusive_group()
    iv_group.add_argument("-x", type=str,
                          help="Name of independent variable, for horizontal axis")
    iv_group.add_argument("-y", type=str,
                          help="Name of independent variable, for vertical axis")

    parser.add_argument("-v", "--values", 
                        nargs="+", type=str,
                        help="Dependent variables to show as stacked bars")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for grouped_stack()")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--save", type=str, 
                        help="Name of interactive .html to save, if different from the datafile base")
    group.add_argument("-T", "--nosave", action="store_true",
                       help="Do not save interactive .html")

    parser.add_argument("-s", "--show", action="store_true", 
                        help="Show interactive .html")
    args = parser.parse_args()

    # Unpack YAML args into dict of keyword args for grouped_multi_lines().
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    return(args)


# In[ ]:


if __name__ == "__main__":
    args = _parse_args()
    print(args)

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
    
    # Configure output file for interactive html.
    outfile = args.save
    if outfile is None:
        # Use datafile name, with .html extension.
        outfile = Path(args.datafile).with_suffix(".html").as_posix()
    title = ", ".join(datavars) + " by " + byvar
    output_file(outfile, title=title, mode='inline')
    
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
    default_bar_colors = [default_color_map[var] for var in datavars]

    fig = iv_dv_figure(
        iv_data = source.data[iv_variable],
        iv_axis = iv_axis
    )

    # Make chart, and link widget to make one set of bars visible.
    bars = grouped_stack(
        fig,
        iv_axis=iv_axis,
        iv_variable=iv_variable,
        bar_variables=datavars,
        source=source,
        view=view_by_factor,
        color=default_bar_colors,
        **args.args)
    
    # Make app that shows widget and chart.
    app = layout([
        [widget],
        [fig]
    ])
    
    if not args.nosave:
        # Save interactive html.
        outfile = args.save
        if outfile is None:
            # Use datafile name, with .html extension.
            outfile = Path(args.datafile).with_suffix(".html").as_posix()
        title = ", ".join(datavars) + " by " + byvar
        output_file(outfile, title=title, mode='inline')
        save(app)
    
    if args.show:
        show(app)


# In[13]:



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
    df_data["date"] = df_data["date"].astype(str)

    factor = "industry"
    
    from base import growth_vars
    df_growth = growth_vars(df_data, columns=["gva", "hours worked", "oph"], 
                            reverse="hours worked", by=factor,
                            reverse_suffix=" (sign reversed)")


    factor_levels = sorted(df_data[factor].unique())
    filter_widget = SlideSelect(options=factor_levels,
                                name=factor + "_filter")  # Show this in a layout.

    fig = iv_dv_figure(
        iv_data = df_growth["date"],
        iv_axis = "x",
    )

    source = ColumnDataSource(df_growth)
    view_by_factor = factor_view(source, factor)
    
    bar_variables = ["gva", "hours worked (sign reversed)"]
    color_map = {v: color for v, color in zip(bar_variables,
                                              palettes.Category20_3)}
    

    vbars = grouped_stack(
        fig,
        iv_axis="x",
        iv_variable="date",
        bar_variables=bar_variables,
        color_map=color_map,

        source=source,
        view=view_by_factor,

        #by=factor,
        #x="year",
        #widget=filter_widget,
        #color_map={},
        #palette=None,
        #fig=None,
        #fig_options={}
    )

    # Make app that shows widget and chart.
    app = layout([
        [filter_widget],
        [fig]
    ])

    show(app)


# In[ ]:


if False:
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


