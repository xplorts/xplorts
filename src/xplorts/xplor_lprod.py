#!/usr/bin/env python
# coding: utf-8

# In[11]:


from bokeh.layouts import column, gridplot, layout
from bokeh.models import CustomJSHover, FactorRange, HoverTool
from bokeh.models.widgets import Div
from bokeh.plotting import figure
from bokeh.io import output_file, show
from bokeh import palettes

import argparse
from collections import defaultdict
import pandas as pd
from pathlib import Path
import textwrap
import re
import yaml

from base import (date_tuples, factor_view, filter_widget, growth_vars, iv_dv_figure, 
                  link_widgets_to_groupfilters, set_output_file, unpack_data_varnames, 
                  variables_cmap)
from lines import grouped_multi_lines, link_widget_to_lines
from slideselect import SlideSelect
from stacks import grouped_stack
from snapcomp  import components_figure, link_widget_to_snapcomp_figure
from tscomp import link_widget_to_tscomp_figure, ts_components_figure


# In[2]:


def index_to(data, baseline, to=100):
    """
    Scale data so values at `baseline` map to `to`
    
    Examples
    --------
    # Index (2001 = 100)
    df = pd.DataFrame(dict(year=[2000, 2001, 2002], jobs=[40, 50, 20]))
    baseline = df.jobs[df.year == 2001].values[0]
    df["jobs_index"] = index_to(df.jobs, baseline)
    df
    #    year  jobs  jobs_index
    # 0  2000    40        80.0
    # 1  2001    50       100.0
    # 2  2002    20        40.0
    """
    
    return data / baseline * to

def growth_pct_from(data, baseline):
    """
    Percentage growth from baseline data
    
    ## Year on year growth
    df = pd.DataFrame(dict(year=[2000, 2001, 2002], jobs=[40, 50, 20]))
    baseline = df.jobs[df.year == 2001].values[0]
    df["jobs_yoy"] = growth_pct_from(df, baseline)
    
    ## Cumulative growth for two columns
    df = pd.DataFrame(dict(
        year=[2000, 2001, 2002], 
        jobs=[40, 50, 20], 
        gva=[200, 250, 275]))
    baseline = df.loc[df.year == df.year.min(), ("jobs", "gva")].reindex(index=df.index, method="nearest")
    df[["jobs_growth", "gva_growth"]] = growth_pct_from(df[["jobs", "gva"]], baseline)
    df
    """
    
    return (data / baseline - 1) * 100


def _cumulative_growth(data, columns, date_var="date"):
    # Wrap single column name in a list, for convenience.
    columns = [columns] if isinstance(columns, str) else columns
    
    # Classify each row as having the earliest date or not.
    is_min_date = data[date_var] == data[date_var].min()
    
    # Calculate baseline for each column from row with earliest date.
    return growth_pct_from(data[columns], date_var="date",
                           baseline="first")

def _window_growth():
    pass


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
        description="Create interactive visualiser for labour productivity levels with a split factor"
    )
    parser.add_argument("datafile", 
                        help="File (CSV) with data series and split factor")
    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")
    parser.add_argument("-p", "--lprod", type=str,
                        help="Productivity variable")    
    parser.add_argument("-v", "--gva", 
                        type=str,
                        help="Gross value added (GVA) variable")
    parser.add_argument("-l", "--labour", 
                        type=str,
                        help="Labour variable (e.g. jobs or hours worked)")
    parser.add_argument("-g", "--args", 
                        type=str,
                        help="Keyword arguments(?)")

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


# In[ ]:


def prod_ts_lines(data, 
                  widget=None, 
                  varnames=None,
                  date=None, 
                  by=None, 
                  data_variables=None, 
                  lprod=None,
                  gva=None,
                  labour=None,
                  color_map=None,
                  **kwargs):
    """
    Make interactive line chart of productivity data
    
    Parameters
    ----------
    data : DataFrame
        Including columns to be plotted, which are named in other parameters.
    widget : Bokeh widget, optional
        The `value` attribute will be linked to the chart to make visible one
        value of the `by` variable.
    varnames : dict, optional
        Mapping to specify column names for 'by', 'date', and either 
        'data_variables' or the three individual data variables 'lprod',
        'gva', and 'labour'.
    date : str, optional
        Name of column containing time series dates to plot along the horizontal
        chart axis.  If not given, `varnames["date"]` is used.
    by : str, optional
        Name of column containing split levels.  The chart displays a single split
        level at a time.  If not given, `varnames["by"]` is used.
    data_variables : list, optional
        List of three column names to be plotted as time series lines.  The columns
        should be, in order, labour productivity, gross value added, and labour.  If
        not given, the column names should be specified via the `varnames` parameter
        or via `lprod`, `gva`, and `labour` parameters.
    lprod, gva, labour : str, optional
        Name of column containing values to be plotted as a time
        series line.  If not given, the value is looked up in `varnames`.  Ignored if
        `data_variables` is specified.
    kwargs : mapping
        Keyword arguments passed to `iv_dv_figure()`.
    
    Returns
    -------
    Bokeh figure.
    """
    
    if date is None:
        date = varnames["date"]
    if by is None:
        by = varnames["by"]
    if data_variables is None:
        if lprod is None:
            lprod = varnames["lprod"]
        if gva is None:
            gva = varnames["gva"]
        if labour is None:
            labour = varnames["labour"]
        data_variables = [lprod, gva, labour]
    
    # Transform monthly and quarterly dates to nested categories.
    datevar = varnames["date"]
    data_local = data.copy()
    data_local["_date_factor"] = date_tuples(data_local[datevar],
                                             length_threshold=DATE_THRESHOLD)

    # Prepare to suppress most quarters or months on axis if lots of them.
    suppress_factors = (isinstance(data_local["_date_factor"][0], tuple)
                        and len(data_local["_date_factor"].unique()) > 40)
    
    ## Show index time series on line chart, split by industry.
    fig_index_lines = iv_dv_figure(
        iv_data = data_local["_date_factor"],
        iv_axis = "x",
        suppress_factors = suppress_factors,
        title = "Productivity, gross value added and labour",
        #x_axis_label = kwargs.pop("x_axis_label", date),
        y_axis_label = kwargs.pop("y_axis_label", "Value"),
        **kwargs
    )
    
    if color_map is None:
        palette = palettes.Category20_3[::-1]
    else:
        palette = [color_map[var] for var in ("lprod", "gva", "labour")]

    cds_options = {
        "color": palette,
        "line_dash": ["solid", "solid", "dashed"]}

    index_lines = grouped_multi_lines(
        fig_index_lines,
        data_local, 
        iv_variable=dict(plot="_date_factor", hover=datevar),
        data_variables=data_variables,
        by=by,
        cds_options=cds_options,
        color="color",
        line_dash="line_dash",
        alpha=0.8,
        hover_alpha=1,
        line_width=2,
        hover_line_width=4,
    )

    if widget is not None:
        link_widget_to_lines(widget, index_lines)
    return fig_index_lines


# In[ ]:


def prod_ts_growth(data, 
                  widget=None, 
                  varnames=None,
                  date=None, 
                  by=None, 
                  lprod=None,
                  gva=None,
                  labour=None,
                  color_map=None,
                  reverse_suffix=" (sign reversed)",
                  **kwargs):
    """
    Make interactive time series vertical bar chart of productivity growth components
    
    Parameters
    ----------
    data : DataFrame
        Including columns to be plotted, which are named in other parameters.
    widget : Bokeh widget, optional
        The `value` attribute will be linked to the chart to make visible one
        value of the `by` variable.
    varnames : dict, optional
        Mapping to specify column names for 'by', 'date', and the three 
        individual data variables 'lprod', 'gva', and 'labour'.
    date : str, optional
        Name of column containing time series dates to plot along the horizontal
        chart axis.  If not given, `varnames["date"]` is used.
    by : str, optional
        Name of column containing split levels.  The chart displays a single split
        level at a time.  If not given, `varnames["by"]` is used.
    lprod, gva, labour : str, optional
        Name of column containing values to be plotted as a time
        series line.  If not given, the value is looked up in `varnames`.
    kwargs : mapping
        Keyword arguments passed to `iv_dv_figure()`.
    
    Returns
    -------
    Bokeh figure.
    """
    
    if date is None:
        date = varnames["date"]
    if by is None:
        by = varnames["by"]
    if lprod is None:
        lprod = varnames["lprod"]
    if gva is None:
        gva = varnames["gva"]
    if labour is None:
        labour = varnames["labour"]
    
    # Transform monthly and quarterly dates to nested categories.
    datevar = varnames["date"]
    data_local = data.copy()
    data_local["_date_factor"] = date_tuples(data_local[datevar],
                                             length_threshold=DATE_THRESHOLD)

    # Prepare to suppress most quarters or months on axis if lots of them.
    suppress_factors = (isinstance(data_local["_date_factor"][0], tuple)
                        and len(data_local["_date_factor"].unique()) > 40)
    
    # Reverse sign of denominator variable (into new dataframe).
    labour_reversed = labour + reverse_suffix
    data_local = data_local.assign(**{labour_reversed: -data_local[labour]})
    
    bar_variables = [gva, labour_reversed]

    ## Show time series growth components (bars) and total (line).
    fig_combi = iv_dv_figure(
        iv_data = data_local["_date_factor"],
        iv_axis = "x",
        suppress_factors = suppress_factors,
        title = "Cumulative growth",
        x_axis_label = kwargs.pop("x_axis_label", date),
        y_axis_label = kwargs.pop("y_axis_label", "Growth (percent)"),
        **kwargs
    )
    
    if color_map is None:
        palette = palettes.Category20_3[::-1]
    else:
        palette = [color_map[var] for var in ("lprod", "gva", "labour")]

    growth_combi = ts_components_figure(
        fig_combi,
        data_local,
        date_variable=dict(plot="_date_factor", hover=datevar),
        bar_variables=bar_variables,
        line_variable=lprod,
        by=by,
        line_args={"color": palette[0]},
        bar_args={"color": palette[1:]}
    )

    if widget is not None:
        link_widget_to_tscomp_figure(widget, fig_combi)

    return fig_combi


# In[ ]:


def prod_growth_snapshot(data, 
                        widget=None, 
                        varnames=None,
                        date=None, 
                        by=None, 
                        lprod=None,
                        gva=None,
                        labour=None,
                        color_map=None,
                        reverse_suffix=" (sign reversed)",
                        **kwargs):
    """
    Make interactive snapshot horizontal bar chart of productivity growth components
    
    Parameters
    ----------
    data : DataFrame
        Including columns to be plotted, which are named in other parameters.
    widget : Bokeh widget, optional
        The `value` attribute will be linked to the chart to make visible one
        value of the `date` variable.
    varnames : dict, optional
        Mapping to specify column names for 'by', 'date', and the three 
        individual data variables 'lprod', 'gva', and 'labour'.
    date : str, optional
        Name of column containing time series dates.  The chart displays a single
        date at a time.  If not given, `varnames["date"]` is used.
    by : str, optional
        Name of column containing split levels, which are displayed along the vertical
        axis as a categorical independent variable.  If not given, `varnames["by"]` is 
        used.
    lprod, gva, labour : str, optional
        Name of column containing values to be plotted as horizontal bars or markers.  
        If not given, the value is looked up in `varnames`.
    kwargs : mapping
        Keyword arguments passed to `iv_dv_figure()`.
    
    Returns
    -------
    Bokeh figure.
    """
    
    if date is None:
        date = varnames["date"]
    if by is None:
        by = varnames["by"]
    if lprod is None:
        lprod = varnames["lprod"]
    if gva is None:
        gva = varnames["gva"]
    if labour is None:
        labour = varnames["labour"]
    
    # Reverse sign of denominator variable (into new dataframe).
    labour_reversed = labour + reverse_suffix
    data_local = data.copy()
    data_local[labour_reversed] = -data_local[labour]
    
    bar_variables = [gva, labour_reversed]

    ## Show snapshot of latest growth components as hbars by industry.
    fig_snapshot = iv_dv_figure(
        iv_data = reversed(data_local[by].unique()),  # From top down.
        iv_axis = "y",
        title = "Period-on-period growth",
        x_axis_label = kwargs.pop("y_axis_label", "Growth (percent)"),
        y_axis_label = kwargs.pop("x_axis_label", by),
        legend_place = "above",
        **kwargs
    )
    
    if color_map is None:
        palette = palettes.Category20_3[::-1]
    else:
        palette = [color_map[var] for var in ("lprod", "gva", "labour")]
    
    snapshot_renderers = components_figure(
        fig_snapshot,
        data_local,
        by=date,
        marker_variable=lprod,
        y=by,
        bar_variables=bar_variables,
        scatter_args={"color": palette[0]},
        bar_args={"color": palette[1:]},
    )

    if widget is not None:
        link_widget_to_snapcomp_figure(widget, fig_snapshot)

    return fig_snapshot


# In[ ]:


if __name__ == "__main__":
    # Running from command line (or in Notebook?).
    
    # Suppress quarterly or monthly axis labels for time series longer than this.
    DATE_THRESHOLD = 40
    
    args = _parse_args()
    print(args)

    # Read the data as is.
    data = pd.read_csv(args.datafile, dtype=str)
    
    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "lprod", "gva", "labour"],
        data.columns)
    
    datevar = varnames["date"]
    dependent_variables = [varnames[var] for var in ("lprod", "gva", "labour")]
    
    #title = ", ".join(dependent_variables) + " by " + varnames["by"]
    title = "xplor lprod: " + Path(args.datafile).stem
    
    # Configure output file for interactive html.
    set_output_file(
        args.save or args.datafile,
        title = title
    )

    # Make palettes.
    color_map = variables_cmap(["labour", "gva", "lprod"],
                               palettes.Category20_3)
    
    # Convert str to float so we can plot the data.
    data[dependent_variables] = data[dependent_variables].astype(float)

    
    # Widget for `by`.
    split_widget = filter_widget(data[varnames["by"]], title=varnames["by"])

    # Widget for date.
    date_widget = filter_widget(data[datevar], start_value="last")

    fig_index_lines = prod_ts_lines(
        data, 
        varnames=varnames,
        color_map=color_map,
        widget=split_widget, 
        height=300, width=600,
        **args.args["lines"])


    # Calculate cumulative growth.
    df_growth_cum = growth_vars(data,
                            date_var=datevar,
                            columns=dependent_variables, 
                            by=varnames["by"],
                            baseline="first",
                           )

    fig_ts_growth = prod_ts_growth(
        df_growth_cum,
        varnames=varnames, 
        color_map=color_map,
        widget=split_widget, 
        height=300, width=600,
        **args.args["growth_series"])


    # Calculate period-on-period growth.
    df_growth = growth_vars(data,
                            date_var=datevar,
                            columns=dependent_variables, 
                            by=varnames["by"],
                            periods=1,
                           )
    
    # Truncate long levels of `by`, for axis labels.
    by_var = varnames["by"]
    df_growth[by_var] = df_growth[by_var].apply(
        textwrap.shorten, args=(15,), placeholder='..'
    )
    
    fig_growth_snapshot = prod_growth_snapshot(
        df_growth,
        varnames=varnames, 
        color_map=color_map,
        widget=date_widget, 
        height=600, width=300,
        **args.args["growth_snapshot"])

    # Make app that shows widget and charts.
    ts_charts = column(split_widget, fig_index_lines, fig_ts_growth)
    snapshot = column(date_widget, fig_growth_snapshot)
    app = layout([
        Div(text="<h1>" + title),  # Show title as level 1 heading.
        [ts_charts, snapshot], 
    ])
    
    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.


# In[4]:


if False:
    by = "industry"

    data_variables = ["oph", "gva", "hours"]
    line_var = "oph"
    bar_vars = [name for name in df_growth.columns                         if name not in (by, "date", line_var)]
    growth_variables = [line_var, *bar_vars]

    ref_date = df_index[datevar].min()
    y_axis_label = f"Index ({ref_date} = 100)"

    filter_widget = SlideSelect(options=sorted(df_index[by].unique()),
                                title=by,  # Shown.
                                name=by + "_filter")  # Internal.

    date_widget = SlideSelect(options=sorted(df_index[datevar].unique()),
                                title=datevar,  # Shown.
                                name=datevar + "_filter")  # Internal.
    date_widget.value = date_widget.options[-1]

    ## Show index time series on line chart, split by industry.
    fig_index_lines = iv_dv_figure(
        iv_data = sorted(df_index[datevar].unique()),
        iv_axis = "x",
        height=300, width=500,
        y_axis_label=y_axis_label,
    )

    index_lines = grouped_multi_lines(
        fig_index_lines,
        df_index, 
        iv_variable=datevar,
        data_variables=data_variables,
        by=by,
        cds_options={"color": palettes.Category20_3[::-1],
                     "line_dash": ["solid", "solid", "dashed"]},
        color="color",
        line_dash="line_dash",
        alpha=0.8,
        hover_alpha=1,
        line_width=2,
        hover_line_width=4,
    )

    link_widget_to_lines(filter_widget, index_lines)


    ## Show time series growth components (bars) and total (line).
    fig_combi = iv_dv_figure(
        iv_data = sorted(df_growth[datevar].unique()),
        iv_axis = "x",
        height=300, width=500,
        y_axis_label=y_axis_label,
    )

    growth_combi = ts_components_figure(
        fig_combi,
        df_growth,
        date_variable=datevar,
        bar_variables=bar_vars,
        line_variable=line_var,
        by=by,
        line_args={"color": palettes.Category20_3[-1]},
        bar_args={"color": palettes.Category20_3[0:2][::-1]}
    )

    link_widget_to_tscomp_figure(filter_widget, fig_combi)

    ## Show snapshot of latest growth components as hbars by industry.
    fig_snapshot = iv_dv_figure(
        iv_data = df_growth[by].unique(),
        iv_axis = "y",
        height=600, width=300,
    )
    snapshot_renderers = components_figure(
        fig_snapshot,
        df_growth,
        by=datevar,
        marker_variable=line_var,
        y=by,
        bar_variables=bar_vars,
        scatter_args={"color": palettes.Category20_3[-1]},
        bar_args={"color": palettes.Category20_3[0:2][::-1]},
    )

    link_widget_to_snapcomp_figure(date_widget, fig_snapshot)


    # Make app that shows widget and charts.
    ts_charts = column(filter_widget, fig_index_lines, fig_combi)
    snapshot = column(date_widget, fig_snapshot)
    app = layout([
        [ts_charts, snapshot], 
    ])

    show(app)

