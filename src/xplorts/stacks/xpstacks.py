"""
Make standalone interactive stacked bar charts for categorical data.

When imported as a module, the function `grouped_stack()` is defined.

When run from the command line, `stacks` reads data from a `csv` file
and creates an HTML document that displays an interactive stacked bar chart.

    The `stacks` command reads data from a `csv` file.  The first row
    of data defines column names.  The file should include:
        - a column of category names for an independent variable,
        - a column of category names for a split factor, and
        - one or more columns of data values to be plotted as stacked bars
          against the independent variable.  The data values can include a
          mix of positive and negative values.

    An interactive chart is created, with widgets to select one of the
    split factor category names (from a pulldown list or a slider), and a
    chart with stacked bars for the value columns.  The independent variable
    can be plotted along either the vertical or horizontal axis.


Command line interface
----------------------
usage: stacks.py [-h] [-b BY] [-x X | -y Y] [-v VALUES [VALUES ...]] [-g ARGS]
                 [-t SAVE] [-s]
                 datafile

Create interactive stacked bars for data series with a split factor

positional arguments:
  datafile              Name of .csv file with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Name of factor variable for splits
  -x X                  Name of independent variable, for horizontal axis
  -y Y                  Name of independent variable, for vertical axis
  -v VALUES [VALUES ...], --values VALUES [VALUES ...]
                        Dependent variables to show as stacked bars
  -g ARGS, --args ARGS  Keyword arguments for grouped_stack(), specified as
                        YAML mapping
  -t SAVE, --save SAVE  Name of interactive .html to save, if different from
                        the datafile base
  -s, --show            Show interactive .html
"""

#%%

from bokeh.layouts import layout
from bokeh.models import ColumnDataSource
from bokeh import palettes
from bokeh.io import save, show
from bokeh.models.widgets import Div

import argparse
import pandas as pd
from pathlib import Path
import sys
import yaml

## Imports from this package
from xplorts.stacks import grouped_stack
from xplorts.base import (factor_view, iv_dv_figure,
                          link_widgets_to_groupfilters, set_output_file, variables_cmap)
from xplorts.slideselect import SlideSelect

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
        prog="python -m xplorts.stacks",
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
                        help="Keyword arguments for grouped_stack(), specified as YAML mapping")


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
        # Get byvar and datavars from explicit arguments, and either x or y.
        byvar = args.by
        datavars = args.values
        if args.x is not None:
            iv_axis = "x"
            iv_variable = args.x
        else:
            iv_axis = "y"
            iv_variable = args.y

    title = "stacks: " + Path(args.datafile).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Make a slide-select widget to choose factor level.
    widget = SlideSelect(options=list(data[byvar].unique()),
                         name=byvar + "_select")

    source = ColumnDataSource(data)
    view_by_factor = factor_view(source, byvar)

    link_widgets_to_groupfilters(widget,
                                 source=source,
                                 filter=view_by_factor.filters)

    # Map variables to colors.
    default_color_map = variables_cmap(datavars,
                                       "Category10_10")
    default_bar_colors = [default_color_map[var] for var in datavars]

    # Labels for axis.
    iv_data = data[iv_variable].unique()
    iv_data = reversed(iv_data) if iv_axis == "y" else list(iv_data)

    fig = iv_dv_figure(
        iv_data = iv_data,
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
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        [widget],
        [fig]
    ])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

#%%

if __name__ == "__main__":
    sys.exit(main())

#%%  Move to test.

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
