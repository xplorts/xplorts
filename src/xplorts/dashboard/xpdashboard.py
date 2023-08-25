"""
Make standalone interactive charts for time series data

When run from the command line, reads data from a CSV file and
creates an HTML document that displays time series levels and cumulative
growth components for one level of a split factor at a time, as well as
a snapshot of growth components across all levels of the split factor for
one time period.

    In the CSV file, the first row of data defines column names.
    The file should include:
        - a column of dates (annual, quarterly or monthly),
        - a column of category names, and
        - one or more columns of data values to be plotted against dates.

    An interactive chart is created, with widgets to select one of the
    category names (from a pulldown list or a slider).  The chart shows
    one line for each value column, with dates plotted along the horizontal
    axis.

    The interactive chart is saved as an HTML file which requires
    a web browser to view, but does not need an active internet connection.
    Once created, the HTML file does not require Python,
    so it is easy to share the interactive chart.

Command line interface
----------------------
usage: xp-dbprod [-h] [-b BY] [-d DATE] [-y DV] [-c NAME] [--c NAME CWEIGHT] [---c NAME CWEIGHT CNAME] [-g ARGS] [-t SAVE] [-s] datafile

Create interactive visualiser for productivity levels with a split factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            show this help message and exit
  -b BY, --by BY        Factor variable for splits
  -d DATE, --date DATE  Date variable
  -y DV, --dv DV        Dependent variable
  -c NAME
  --c NAME CWEIGHT
  ---c NAME CWEIGHT CNAME
                        Component variable whose growth affects `dv`, with optional component weight and name. Specify each component variable with
                        its own -c option. '--c NAME -1' specifies a sign-reversed component that displays on growth charts as 'NAME (sign
                        reversed)'. '---c NAME rev' displays on growth charts as 'NAME rev'.
  -g ARGS, --args ARGS  Keyword arguments. YAML mapping of mappings. The keys 'lines', 'growth_series' and 'growth_snapshot' can provide keyword
                        arguments to pass to `prod_ts_lines`, `prod_ts_growth` and `prod_growth_snapshot`, respectively.
  -t SAVE, --save SAVE  Interactive .html to save, if different from the datafile base
  -s, --show            Show interactive .html


Functions
---------
dashboard_tabs

main
"""

#%%
# Bokeh imports.
from bokeh.layouts import column, grid, layout, row
from bokeh.models import TabPanel, Tabs
from bokeh.models.widgets import Div
from bokeh.io import save, show
from bokeh import palettes

# Other external imports.
import argparse
from collections import defaultdict
import pandas as pd
from pathlib import Path
import sys
import textwrap
import yaml

# Internal imports.
from ..base import (filter_widget,
                          set_output_file, unpack_data_varnames,
                          variables_cmap)
from ..growthcomps import growth_vars, GrowthComponent
from ..heatmap import figheatmap
from ..lines import figlines
from ..snapcomp import figsnapcomp
from ..tscomp import figtscomp

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
        prog="xp-dbprod",
        description="Create interactive visualiser for productivity levels with a split factor"
    )
    parser.add_argument("datafile",
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")
    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")

    parser.add_argument("-y", "--dv", type=str,
                        help="Dependent variable")

    # parser.add_argument("-c", "--iv", type=str,
    #                     nargs="+",  # varname [cweight [cname]]
    #                     metavar=("NAME","CWEIGHT [CNAME]]"),
    #                     action="append",  # Produce list of lists.
    #                     help="""Component variable, with optional contribution weight
    #                         and contribution name.  Specify each component variable with
    #                         its own -c option.  '-c NAME -1' specifies a sign-reversed
    #                         contribution.""")
    parser.add_argument(
        "-c", nargs=1, metavar="NAME",
        dest="iv", action="append", type=str,
        help="")
    parser.add_argument(
        "--c", nargs=2, metavar=("NAME", "CWEIGHT"),
        dest="iv", action="append", type=str,
        help="")
    parser.add_argument(
        "---c", nargs=3, metavar=("NAME", "CWEIGHT", "CNAME"),
        dest="iv", action="append", type=str,
        help="""
        Component variable whose growth affects `dv`, with optional component
        weight and name.  Specify each component variable with
        its own -c option.  '--c NAME -1' specifies a sign-reversed
        component that displays on growth charts as 'NAME (sign reversed)'.
        '---c NAME -1 "{name} rev"' displays on growth charts as 'NAME rev'.
        """)

    parser.add_argument("-g", "--args",
                        type=str,
                        help="""Keyword arguments.  YAML mapping of mappings.  The
                            keys 'lines', 'growth_series' and 'growth_snapshot'
                            can provide keyword arguments to pass to
                            `prod_ts_lines`, `prod_ts_growth` and
                            `prod_growth_snapshot`, respectively.""")

    parser.add_argument("-t", "--save", type=str,
                        help="Interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true",
                        help="Show interactive .html")

    args = parser.parse_args()

    # Unpack YAML args into dict of dict of keyword args for various figures.
    # Will return an empty dict for keys not specified in --args option.
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    args.args = defaultdict(dict, args.args)

    return(args)


#%%

# Height and width of main charts (levels, heatmaps)
_FIG_HEIGHT = 600
_FIG_WIDTH = 900

def dashboard_tabs(data, *,
                   by,
                   date,
                   dv,
                   components,
                   split_widget=None,
                   date_widget=None,
                   color_map=None,
                   ):
    """
    Create tabs of figures and widgets to explore time series data

    Parameters
    ----------
    data : Dataframe
        Time series levels, with date and split variables.
    by : str
        Name of categorical split variable.
    date : str
        Name of categorical date variable.
    dv : str
        Name of dependent variable.
    components : [GrowthComponents]
        Components contributing to the dependent variable.
    split_widget : Bokeh widget, optional
        Widget to select a level of the `by` varible to show. If not given,
        a widget is created.
    date_widget : Bokeh widget, optional
        Widget to select a level of the `date` varible to show. If not given,
        a widget is created.
    color_map : dict, optional
        Mapping of column names to colors. If not given, a default mapping
        is used.

    Returns
    -------
    dict
        Container for Tabs showing 'level', 'growth', and 'cumgrowth'.

    """
    component_names = [c.name for c in components]
    data_variables = [dv] + component_names

    # Widget for `by`.
    if split_widget is None:
        split_widget = filter_widget(data[by], title=by)

    # Widget for date.
    if date_widget is None:
        date_widget = filter_widget(data[date], start_value="last")

    if color_map is None:
        # Use special color for dv.
        c20 = palettes.Category20_20
        category_colors = c20[2:3] + c20[:2] + c20[4:]
        color_map = variables_cmap(data_variables,
                                   category_colors)

    # Map colors for growth components to the colors for corresponding levels.
    color_map.update({c.cname: color_map[c.name] for c in components
                      if c.cname != c.name})

    # Make list of line dash specs, for dv solid, and alternating components.
    line_dash = ["solid"] + ["solid" if i & 1 else "dashed"
                             for i in range(len(components))]

    fig_index_lines = figlines(data,
                    widget=split_widget,
                    date=date,
                    by=by,
                    data_variables=data_variables,
                    color_map=color_map,
                    line_dash = line_dash,
                    iv_dv_args = {
                        "height": _FIG_HEIGHT,
                        "width": _FIG_WIDTH,
                        }
                    )

    # Calculate cumulative growth.
    growth_columns = [
        dv,
        *components
        ]
    df_growth_cum = growth_vars(data,
                            date_var=date,
                            columns=growth_columns,
                            by=by,
                            baseline="first",
                           )

    fig_ts_growth = figtscomp(df_growth_cum,
                date=date,
                by=by,
                bars = [c.cname for c in components],
                line=dv,
                widget=split_widget,
                iv_dv_args = {
                    "title": "Cumulative growth",
                    "height": _FIG_HEIGHT // 2,
                    "width": _FIG_WIDTH,
                    },
                color_map = color_map,
                )


    # Calculate period-on-period growth.
    df_growth = growth_vars(data,
                            date_var=date,
                            columns=growth_columns,
                            by=by,
                            periods=1,
                           )

    # Truncate long levels of `by`, for axis labels.
    df_growth[by] = df_growth[by].apply(
        textwrap.shorten, args=(15,), placeholder='..'
    )

    fig_growth_snapshot = figsnapcomp(
        df_growth,
        by=by,
        date=date,
        bars = [c.cname for c in components],
        markers=dv,
        color_map=color_map,
        widget=date_widget,
        iv_dv_args = {
            "title": "Period-on-period growth",
            "height": _FIG_HEIGHT,
            "width": _FIG_WIDTH // 3,
            })

    # Put level and growth charts, with widgets, on a tab.
    ts_charts = column(split_widget, fig_index_lines, fig_ts_growth)
    snapshot = column(date_widget, fig_growth_snapshot)
    tab_levels = TabPanel(
        title="Levels",
        child=layout([
            [ts_charts, snapshot],
            ]))


    ## Growth heatmap tab.
    growth_heatmap = figheatmap(
        df_growth,
        x=date,
        y=by,
        values=dv,
        x_widget=date_widget.handle,
        y_widget=split_widget.handle,
        title=dv + " growth",
        figure_options=dict(width=_FIG_WIDTH, height=_FIG_HEIGHT),
        )
    tab_growth = TabPanel(
        title="Growth heatmap",
        child=row([growth_heatmap, fig_growth_snapshot, date_widget.handle]),
        )


    ## Cumulative growth heatmap tab.
    cum_growth_heatmap = figheatmap(
        df_growth_cum,
        x=date,
        y=by,
        values=dv,
        x_widget=date_widget.handle,
        y_widget=split_widget.handle,
        title=dv + " cumulative growth",
        figure_options=dict(width=_FIG_WIDTH, height=_FIG_HEIGHT),
        )
    tab_cum_growth = TabPanel(
        title="Cum growth heatmap",
        child=grid([[cum_growth_heatmap, None],
                      [fig_ts_growth, split_widget.handle]]),
        )

    return {
        "levels": tab_levels,
        "growth": tab_growth,
        "cumgrowth": tab_cum_growth,
        }

#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40

def main():
    args = _parse_args()

    # Read the data as is.
    data = pd.read_csv(args.datafile, dtype=str)

    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "dv"],
        data.columns)

    date = varnames["date"]
    by = varnames["by"]
    dv = varnames["dv"]

    # Unpack component variables, into a list of GrowthComponents
    components = [GrowthComponent(*iv) for iv in args.iv]
    data_vars = [dv] + [c.name for c in components]

    title = "xplor prod: " + Path(args.datafile).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Convert str to float so we can plot the data.
    data[data_vars] = data[data_vars].astype(float)

    tabs = dashboard_tabs(data,
                           by=by,
                           date=date,
                           dv=dv,
                           components=components,
                           )

    # Make app that shows tabs of various charts.
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        Tabs(tabs=list(tabs.values()))
        ])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

#%%

if __name__ == "__main__":
    # Running from command line (or in Notebook?).
    sys.exit(main())
