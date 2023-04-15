#!/usr/bin/env python
# coding: utf-8

# In[ ]:


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


# In[15]:


from bokeh.core.properties import expr
from bokeh.layouts import gridplot, layout
from bokeh.models import (CDSView, ColumnDataSource, CustomJS, CustomJSExpr,
                          CustomJSFilter, CustomJSTransform, GroupFilter,
                          Legend, LegendItem, Select)
from bokeh import palettes
from bokeh.plotting import figure
from bokeh.io import output_notebook, show
from bokeh.transform import factor_cmap, stack

import argparse
from itertools import tee, zip_longest
import numpy as np
import pandas as pd
import re
import yaml

## Find slideselect module near current working directory.
from pathlib import Path
import sys
import_folder = (Path.cwd() / "../Chart_browser").as_posix()
if import_folder not in sys.path:
    sys.path.append(import_folder)
from slideselect import SlideSelect

from grouped_multi_lines import grouped_multi_lines

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


# In[2]:


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


# In[3]:


class StackRectified(CustomJSExpr):
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
        obj.__qualified_model__ = "CustomJSExpr"
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
            raise ValueError(f"max_value not allowed for StackGreater, was {kwargs[max_value]}")
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
            raise ValueError(f"min_value not allowed for StackGreater, was {kwargs[min_value]}")
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


# In[4]:



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


# In[5]:


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


# In[6]:


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


# In[7]:


def grouped_stack(data,
                data_variables,
                x="date",
                y=None,
                by=None,
                widget=None,
                color_map={},
                palette=None,
                fig=None,
                fig_options={}):
    """
    Grouped renderers for stacked bar charts with data that may be positive or negative
    """
    
    if fig is None:
        # Build figure from default and specified options.
        fopts = dict(
            background_fill_color = "#fafafa",
            tools = ["box_select", "hover", "reset"],
            x_axis_type = "datetime",
            **fig_options
        )
        fig = figure(**fopts)
        
    bar_direction = "vbars" if y is None else "hbars"

    # Identify color palette from argument or default.
    if palette is None:
        # Use minimum colors necessary from Category10.
        palette = palettes.Category10_10[:min(len(data_variables), 10)]
    elif isinstance(palette, str):
        # Access named palette from bokeh.palettes.
        palette = getattr(palettes, palette)
    else:
        # Assume palette is valid as is.
        pass

    # Map chart variables (e.g. oph, gva, hours) to palette colors, overridden as appropriate.
    default_color_map = {
        variable: color for variable, color in zip_longest(data_variables, palette)
    }
    color_map = {**default_color_map, **color_map}

    factor_levels = sorted(data[by].unique())

    factor_filter = GroupFilter(
        column_name=by,
        group=factor_levels[0],
        name="factor_filter"
    )

    cds = ColumnDataSource(data)
    factor_view = CDSView(
        source=cds,
        filters=[factor_filter])

    stack_args = dict(
        source=cds,
        view=factor_view,
        width=1000*60*60*24*80,  # 1000 msec x 60 sec x 60 min x 24 hrs x 80 days, 
        color=list(color_map.values()),
        alpha=0.25
    )
    
    if bar_direction == "vbars":
        bars = vbar_stack_updown(
            fig,
            data_variables,
            **stack_args,
            x=x
        )
    else:
        bars = hbar_stack_updown(
            fig,
            data_variables,
            **stack_args,
            y=y
        )
    
    if widget is not None:
        link_widget_to_filter_group(widget, cds, factor_filter)

    # Add to legend.
    bar_legend_items = [
        # Include legend item for each factor level.
        LegendItem(label=var, 
                   renderers=[bars[2*i]], 
                   index=i) \
        for i, var in enumerate(data_variables)
    ]
    try:
        # Add to existing legend.
        fig.legend.items.extend(bar_legend_items)
    except AttributeError:
        # Build legend from scratch.
        fig.add_layout(Legend(items=bar_legend_items,
                              background_fill_alpha = 0.0))  # Transparent.
        
    fig._stacked = bars

    return fig


# In[8]:


def link_widget_to_filter_group(widget, source, filt):
    # Get widget handle (e.g. for SlideSelect), else link directly to widget.
    filter_handle = getattr(widget, "handle", widget)

    # Link widget value to filter `group`.
    filter_handle.js_link("value", other=filt, other_attr="group")

    # Signal change in data when filter `group` changes, so chart refreshes.
    filt.js_on_change(
        "group",
        CustomJS(args=dict(source=source),
                 code="""
                     source.change.emit()
                 """))    


# In[9]:


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
    parser.add_argument("-x", "--datevar", type=str,
                        help="Name of date variable")
    parser.add_argument("-y", "--bars", 
                        nargs="+", type=str,
                        help="Variables to show as stacked bars")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments for grouped_stack()")
    parser.add_argument("-p", "--palette", 
                        type=str,
                        help="Name of color palette from bokeh.palettes")

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
    if all(getattr(args, arg) is None for arg in ["datevar", "by", "bars"]):
        # Get datevar from first column, byvar from second, datavars from remaining.
        datevar, byvar = data.columns[:2]
        datavars = data.columns[2:]
    else:
        # Get byvar and datavars from explicit arguments, and optionally datevar too.
        byvar = args.by
        datavars = args.bars
        datevar = "date" if args.datevar is None else args.datevar
    
    ## Convert datevar to datetime, based on first date.
    sample_date = data[datevar][0]
    if re.fullmatch("\d{4} ?Q\d", sample_date.upper()):
        # Quarterly like '2019Q3' or '2019 Q3'.
        period = "Q"
    elif re.fullmatch("\d{4}", sample_date):
        # Annual like '2019'
        period = "A"
    else:
        # Maybe monthly will work.
        period = "M"
    data[datevar] = pd.to_datetime(data[datevar]).dt.to_period(period)
    
    # Make a slide-select widget to choose factor level.
    widget = SlideSelect(options=list(data[byvar].unique()),
                         name=byvar + "_select")
    
    # Make chart, and link widget to make one set of bars visible.
    fig = grouped_stack(data,
                        by=byvar,
                        x=datevar,
                        data_variables=datavars,
                        palette=args.palette,
                        widget=widget,
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
        output_file(outfile, title=title)
        save(app)
    
    if args.show:
        show(app)


# In[14]:


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

    df_growth.to_csv("oph_gva_hours_growth_by_ab.csv")


# In[12]:


if False:

    (line_var, *bar_vars) = growth_variables

    filter_widget = SlideSelect(options=factor_levels,
                                name=factor + "_filter")  # Show this in a layout.

    fig = grouped_stack(
        df_growth,
        bar_vars,
        x="date",
        by=factor,
        widget=filter_widget,
        color_map={},
        palette=None,
        fig=None,
        fig_options={}
    )


    # Make app that shows widget and chart.
    app = layout([
        [filter_widget],
        [fig]
    ])

    show(app)

