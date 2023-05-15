"""
Make standalone interactive charts for time series productivity data

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, `xplprod.py` reads data from a CSV file and
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
usage: xplprod.py [-h] [-b BY] [-d DATE] [-p LPROD] [-v GVA] [-l LABOUR]
                      [-g ARGS] [-t SAVE] [-s]
                      datafile

Create interactive visualiser for labour productivity levels with a split
factor

positional arguments:
  datafile              File (CSV) with data series and split factor

optional arguments:
  -h, --help            Show this help message and exit
  -b BY, --by BY        Factor variable for splits
  -d DATE, --date DATE  Date variable
  -p LPROD, --lprod LPROD
                        Productivity variable
  -v GVA, --gva GVA     Gross value added (GVA) variable
  -l LABOUR, --labour LABOUR
                        Labour variable (e.g. jobs or hours worked)
  -g ARGS, --args ARGS  Keyword arguments.  YAML mapping of mappings.  The
                        keys 'lines', 'growth_series' and 'growth_snapshot' 
                        can provide keyword arguments to pass to
                        `prod_ts_lines`, `prod_ts_growth` and 
                        `prod_growth_snapshot`, respectively.
  -t SAVE, --save SAVE  Interactive .html to save, if different from the
                        datafile base
  -s, --show            Show interactive .html
  

Application program interface (API)
-----------------------------------
prod_growth_snapshot
    Make categorical snapshot chart of productivity growth components.

prod_ts_growth
    Make time series chart of productivity growth components.

prod_ts_lines
    Make line chart of productivity data.
"""

#%%
# Bokeh imports.
from bokeh.layouts import column, layout
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
from .base import (filter_widget, iv_dv_figure, 
                          set_output_file, unpack_data_varnames, 
                          variables_cmap)
from .dutils import date_tuples, growth_vars
from .lines import grouped_multi_lines, link_widget_to_lines
from .snapcomp  import components_figure, link_widget_to_snapcomp_figure
from .tscomp import link_widget_to_tscomp_figure, ts_components_figure

#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40


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
                        and len(data_local["_date_factor"].unique()) > DATE_THRESHOLD)
    
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

#%%

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
                        and len(data_local["_date_factor"].unique()) > DATE_THRESHOLD)
    
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

    ts_components_figure(
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


#%%

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
    
    components_figure(
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


#%%
def main():
    args = _parse_args()

    # Read the data as is.
    data = pd.read_csv(args.datafile, dtype=str)
    
    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "lprod", "gva", "labour"],
        data.columns)
    
    datevar = varnames["date"]
    dependent_variables = [varnames[var] for var in ("lprod", "gva", "labour")]
    
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

#%%

if __name__ == "__main__":
    # Running from command line (or in Notebook?).
    sys.exit(main())
