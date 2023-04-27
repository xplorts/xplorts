"""
Base
----
Miscellaneous helpers for interactive time series charts

Functions
---------
accumulate_list
    Initial subsequences of increasing length from list of items.

date_tuples

dict_fill

growth_pct_from
    Percentage growth for a series relative to a baseline value.

index_to
    Scale a series by constant so a baseline value maps to a target value.

growth_vars
unpack_data_varnames
variables_cmap

add_hover_tool
extend_legend_items
factor_filters
factor_view
filter_widget
iv_dv_figure
link_widgets_to_groupfilters
set_output_file

"""


#%%

from bokeh import palettes
import bokeh.palettes

from bokeh.io import output_file
from bokeh.models import (CDSView, ColumnDataSource, CustomJS, GroupFilter, FactorRange, 
                          HoverTool, Legend, LegendItem)
from bokeh.models.formatters import FuncTickFormatter
from bokeh.plotting import figure

from itertools import cycle, tee
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from pathlib import Path

import numpy as np
import pandas as pd
import re

# Imports from this package.
from slideselect import SlideSelect

try:
    from itertools import pairwise
except ImportError:
    # Define local pairwise(), since itertools is too old to have it.
    #
    # Function is derived from
    #   https://docs.python.org/3/library/itertools.html#itertools.pairwise
    # "Copyright © 2001-2023 Python Software Foundation; All Rights Reserved"
    # Used here under the ZERO-CLAUSE BSD LICENSE FOR CODE IN THE PYTHON 3.11.3 DOCUMENTATION
    #   https://docs.python.org/3/license.html#bsd0
    def pairwise(iterable):
        """
        Stand-in for itertools.pairwise()
        
        pairwise('ABCDEFG') --> AB BC CD DE EF FG.
        """
        
        a, b = tee(iterable)
        next(b, None)  # Remove first item of second sequence.
        return zip(a, b)  # Pairs until second sequence is exhausted.


#%%

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
    baseline = data.loc[is_min_date, columns]         .reindex(index=data.index, method="nearest")  # Broadcast baseline to match shape of data.
    return growth_pct_from(data[columns],
                           baseline)

def growth_vars(data, columns=[], date_var=None, by=None, 
                periods=1, baseline=None):
    """
    # Period-on-period
    growth_vars(df, columns=["gva"], date_var="date", periods=1)
    
    # Cumulative growth
    growth_vars(df, columns=["gva"], date_var="date", baseline="first")

    # Growth relative to single date.
    growth_vars(df, columns=["gva"], date_var="date", baseline="2019 Q4")
    
    # Revisions from comparable dataframe.
    growth_vars(df, columns=["gva"], baseline=df_baseline)


    # Growth relative to single date, with a split factor.
    growth_vars(df, columns=["gva"], date_var="date", by="industry", baseline="2019 Q4")
    
    # Same as:
    baseline = data.loc[df["date"]==min(df["date"]), :].groupby("industry")["gva"].first()
    growth_vars(df, columns=["gva"], date_var="date", baseline=baseline)

    
    # Relative to calculated baseline for each level of `by`
    baseline = data.loc[data["year"]=="2019", :].groupby("industry")["gva"].mean()
    growth_vars(df, columns=["gva"], by="industry", baseline=baseline)
    """
    
    # Ensure data columns include the ones we need.
    if date_var is not None:
        assert date_var in data.columns
    if by is not None:
        assert by in data.columns
    assert all(col in data.columns for col in columns),         f"Some of {columns} are missing from data columns {data.columns}"

    
    # Make placeholder copy of data ready to inject results into `columns`.
    result = data.copy()
    result[columns] = np.nan
    
    # Expand baseline shortcuts ("first" or a value to match data[date_var]).
    if baseline == "first":
        # Put baseline at earliest date value to get cumulative growth.
        if by is not None:
            baseline = data.loc[data[date_var]==min(data[date_var]), :].groupby(by)[columns].first()
        else:
            baseline = data.loc[data[date_var]==min(data[date_var]), :]
    elif baseline is not None and not isinstance(baseline, pd.DataFrame):
        # Find column values from date_var == baseline.
        df_baseline_columns = columns + [by] if by is not None else columns
        df_baseline_raw = data.set_index(date_var).loc[baseline, df_baseline_columns]
        if by is not None:
            # Take mean for each of the columns at each level of `by`.
            baseline = df_baseline_raw.groupby(by).mean()
        else:
            # Take mean for each of the columns.
            baseline = df_baseline_raw.mean()
    elif isinstance(baseline, pd.DataFrame):
        # Expect baseline dataframe to have a value for each column, with optional `by` splits.
        pass
    else:
        assert baseline is None
    
    if isinstance(baseline, pd.DataFrame):
        # Get relative change of data compared to baseline dataframe.

        assert all(col in baseline.columns for col in columns),             f"Some of {columns} are missing from baseline columns {baseline.columns}"

        if by is not None and date_var not in baseline.columns:
            # Use `by` to look up baseline rows to find baseline values for columns.
            #  `by` dataframe should have index of `by` levels.
            baseline_values = baseline.loc[data[by], columns].values
        else:
            # Align baseline to data, and compare baseline dataframe to columns.
            join_columns = [date_var, by] if by is not None else [date_var]
            join_keys = list(pd.MultiIndex.from_frame(data[join_columns]))
            baseline_values = baseline.set_index(join_columns).loc[join_keys, columns].values

        result[columns] = growth_pct_from(data[columns],
                                          baseline=baseline_values)
    else:
        # Do period-on-period growth with each column.
        if by is not None:
            sorted_data = data.sort_values(date_var).groupby(by)[columns]
        else:
            sorted_data = data[columns].sort_values(date_var)
        result[columns] = 100 * sorted_data.pct_change(periods=periods)
    return result


# In[3]:


def dict_fill(keys, values):
    """
    Map keys to values, recycling values as necessary
    """
    
    return {key: value for key, value in zip(keys, cycle(values))}

def variables_cmap(variables, palette):
    """
    Map variables to colors
    
    If there are more variables than colors in the palette,
    colors are recycled.
    
    Parameters
    ----------
    variables: str or list[str]
        Variable name or list of names.
    palette: str or array
        Named palette from Bokeh.palettes, or array of colors.
    
    Returns
    -------
    dict mapping variable names to colors.
    """
    
    if isinstance(variables, str):
        # Wrap simple string in a list, for convenience.
        variables = [variables]
    n_data_series = len(variables)
    
    if isinstance(palette, str):
        # Access named palette from bokeh.palettes.
        palette = getattr(palettes, palette)
    
    if isinstance(palette, dict):
        # Extract color palette from palette dict, by number of colors needed.
        last_palette = [palette.values()][-1]
        palette = palette.get(n_data_series, last_palette)

    # Map variables to palette colors, recycling colors as needed.
    color_map = dict_fill(keys=variables, values=palette)
    return color_map


# In[4]:


def iv_dv_figure(
    iv_data = None,
    iv_axis = "x",
    legend = "default",
    legend_place = "center",
    suppress_factors = False,
    **kwargs
):
    """
    Return default figure options, updated with optional keywords
    
    Parameters
    ----------
    iv_data: array or series
        Independent variable against which data will be plotted.  If the
        data provided satisfy pandas `is_datetime()`, the relevant axis type 
        will be "datetime".  Otherwise the default axis type will be used,
        with categorical values and a factor range determined by the unique
        data values.  For regular time periods like annual, quarterly, or
        monthly economic data, a categorical axis is often easier to work
        with and format than a datetime axis.
    iv_axis: str, default "x"
        Whether the independent variable is to be plotted against the "x"
        (horizontal) or "y" (vertical) axis.
    keywords : mapping, optional
        Override default options.
    Returns
    -------
    Bokeh `Figure`.
    """
    
    # Default figure options.
    fopts = dict(
        background_fill_color = "#fafafa",
        tools = "reset,save,pan,box_zoom,wheel_zoom",
    )
    if iv_data is not None:
        # Specify option to configure independent axis.
        if is_datetime(iv_data):
            # Not recommended, but try to accommodate it.
            key = iv_axis + "_axis_type"
            fopts[key] = "datetime"
        else:
            # Use categorical axis (x or y).
            axis_range = pd.Series(iv_data).unique()  # Do not sort.
            key = iv_axis + "_range"
            fopts[key] = FactorRange(factors=axis_range,
                                     factor_padding = 0.2,
                                     group_padding = 0.2,
                                     subgroup_padding = 0.2)

    # Fold in explicit options to override others.
    fopts.update(kwargs)
    fig = figure(**fopts)
    
    if suppress_factors:
        # Suppress most lowest level categorical tick labels.
        # If tick labels are tuples, higher levels will be displayed
        # as normal.
        tf_margins_only = FuncTickFormatter(
            code="""
            if ((index == 0) | (index == ticks.length - 1)) {
                return tick;
            } else {
                return '';
            }
            """
        )
        axis = fig.xaxis if iv_axis == "x" else fig.yaxis
        axis[0].formatter = tf_margins_only

    if legend is not None:
        if legend == "default":
            legend = Legend(
                location = "top_left",
                background_fill_alpha = 0.0)  # Transparent.
        fig.add_layout(legend, place=legend_place)
    
    fig.toolbar.logo = None
    
    return fig


# In[6]:


#class FactorView(GhostBokeh, CDSView):
#    pass

def factor_filters(by, source=None, name_template="filter"):
    """
    Return list of GroupFilter objects for specified variables
    
    Arguments
    ---------
    by: str, sequence, or dict
        Categorical variables to filter by, or a mapping
        from variable names to initial values to use in the
        corresponding filters.  The `dict` form must be
        used if `source` is not given.
    source: ColumnDataSource or DataFrame, optional
        Data to filter.  Ignored if `by` is a `dict`.  Required
        if `by` is not a `dict`.
    name_template: str, optional
        Combined with each `by` variable to assign a name to
        the corresponding filter.  The default is "filter",
        assigning names of the form "filter_X", "filter_Y",
        and so forth, where "X" and "Y" are among the `by`
        variables.
    
    Returns
    -------
    A list of filters that can be used with CDSView tofilter
    a `ColumnDataSource` on values of the `by` variables.
    
    Examples
    --------
    data = pd.DataFrame.from_records(
        [("A", 2001, 10),
         ("A", 2002, 15),
         ("B", 2001, 20),
         ("B", 2002, 18)],
         columns=["industry", "year", "sales"]
    )
    cds = ColumnDataSource(data)
    filters = factor_filters("industry", source=cds)
    view = CDSView(source=cds, filters=filters)
    
    # Explicit initial filter value.
    filters = factor_filters({"industry": "B"})
    )
    """
    
    if isinstance(by, str):
        # Wrap in list, for convenience.
        by = [by]
    
    if not isinstance(by, dict):
        # Map `by` variables to initial values to use in filter.
        data = (source.data if isinstance(source, ColumnDataSource) else data)
        by = {key: next(iter(data[key])) for key in by}

    filters = [
        GroupFilter(
            column_name=var,
            group=initial,
            name="_".join([name_template, var])
        ) \
        for var, initial in by.items() 
    ]
    return filters


def factor_view(source, by, **kwargs):
    """
    Return a CDSView to filter source on specified variables
    
    Parameters
    ---------
    source : ColumnDataSource
        Data to filter.
    by : str or sequence of str
        Categorical variables to filter by.
    kwargs : mapping, optional
        Keyword arguments passed into `factor_filter()`.
    
    Returns
    -------
    A CSDView that filters `source` on values of the `by` variables.
    
    Examples
    --------
    data = pd.DataFrame.from_records(
        [("A", 2001, 10),
         ("A", 2002, 15),
         ("B", 2001, 20),
         ("B", 2002, 18)],
         columns=["industry", "year", "sales"]
    )
    cds = ColumnDataSource(data)
    view = factor_view(cds, "category")
    """
    
    assert isinstance(source, ColumnDataSource), f"source must be ColumnDataSource, not {type(source)}"
    
    view = CDSView(
        source=source,
        filters=factor_filters(by, source=source, **kwargs)
    )
    return view


# In[7]:


def link_widgets_to_groupfilters(widgets, view=None, source=None, filters=None):
    """
    Link values of widgets to corresponding GroupFilter objects
    
    Parameters
    ----------
    widgets : Bokeh widget or list of widgets
        The `value` property of each widget will be linked to the
        `group` property of the corresponding `GroupFilter`.  If there are
        more widgets than filters, the excess widgets are ignored.
    view : CDSView, optional
        Provides `source` and `filters` if they are not specified directly.
    source : ColumnDataSource
        Data source, which will be configured to emit a change signal when
        a filter's `group` property changes, to re-render the relevant figure.
    filters : GroupFilter or sequence of GroupFilter
        The `group` property of each filter will be updated whenever the
        `value` of the corresponding widget changes, and `source` will emit
        a change signal whenever the `group` property of a filter changes.  If
        there are more filters than widgets, excess filters are ignored.
    
    Examples
    --------
    from bokeh.models import ColumnDataSource
    from base import factor_view
    source = ColumnDataSource({"industry": ["A", "B"],
                               "growth": [10, 12]})
    view_by_factor = factor_view(source, "industry")
    widget = SlideSelect(options=["A", "B"],
                         name="industry_filter")  # Show this in a layout.
    link_widgets_to_groupfilters(widget, 
                                 view=view_by_factor)
    
    # Source and filter can be specified directly.
    link_widgets_to_groupfilters(widget, 
                                 source=source,
                                 filters=view_by_factor.filters)
    """

    if all(x is None for x in (view, source, filters)):
        raise ValueError("Must either specify source and filters, or view")
    
    if source is None:
        source = view.source
    
    if filters is None:
        # Find filters in view, assumed to correspond to widgets.
        filters = view.filters
    
    # Wrap singleton widget or filter, for convenience.
    if not isinstance(widgets, (list, tuple)):
        widgets = [widgets]
    if not isinstance(filters, (list, tuple)):
        filters = [filters]
        
    for widget, filt in zip(widgets, filters):
        # Link widget to the GroupFilter.
        assert isinstance(filt, GroupFilter)
        widget.js_link("value", other=filt, other_attr="group")

        # Signal change in data when filter `group` attribute changes, 
        # so chart refreshes.
        filt.js_on_change(
            "group",
            CustomJS(args=dict(source=source),
                     code="""
                         source.change.emit()
                     """))    



# In[8]:


def extend_legend_items(fig, renderers=None, items=None, **kwargs):
    """
    Add legend items to figure
    
    Extends the legend items of a Bokeh figure.
    
    Parameters
    ----------
    fig : Bokeh Figure
        Figure to add legend items to.
    renderers : mapping
        Mapping of labels to renderers, to create `LegendItem`
        objects.  Each value should be a renderer or list of renderers.
        Either `renderers` or `items` must be specified.
        The `renderers` parameter is ignored if `items` are given.  
    items : list of LegendItem
        Will be added to the figure's legend items.
        Either `renderers` or `items` must be specified.
    kwargs : mapping, optional
        Keyword arguments passed to `fig.Legend` if
        `fig` does not already have a legend.
    
    Raises
    ------
    ValueError
        If neither renderers nor items is given.
        
    Example
    -------
    from bokeh.io import show
    from bokeh.models import Legend
    from bokeh.plotting import figure
    fig = figure()
    fig.add_layout(Legend(location="top_left",
                          background_fill_alpha=0.0))
    plot = fig.circle(x=1, y=3)
    extend_legend_items(fig, {"x": plot})
    show(fig)
    """
    
    if renderers is None and items is None:
        raise ValueError("either renderers or items required")
        
    if items is None and renderers is not None:        
        # Make a legend item for each renderer.
        items = [
            # Include legend item for each factor level.
            LegendItem(
                label=var, 
                renderers=renderer if isinstance(renderer, list) else [renderer], 
            ) \
            for var, renderer in renderers.items()
        ]
    
    fig.legend.items.extend(items)
    return None


# In[9]:


def add_hover_tool(fig, renderers, *tooltips, simplify=True, **kwargs):
    """
    Add a hover tool to a Bokeh figure, for given renderers
    
    Parameters
    ----------
    fig : Bokeh Figure
        Figure to add hover tool to.
    renderers : list
        Renderers that should trigger the hover tool.
    tooltips : list or dict
        Positional arguments should be (label, value) tuples for a
        tabular hover tool.  Alternatively, `tooltips` can be
        given as a keyword argument assigned to a mapping of labels
        to values.
    simplify : bool, default True
        Suppress the label of a single (label, value) tooltip, so the
        hover tool shows just the formatted value.  The `simplify`
        flag has no effect if multiple tooltips are given.
    kwargs : mapping, optional
        Additional keyword arguments are passed to `Hovertool()`.
    """

    if isinstance(tooltips, dict):
        # Convert mapping to list of (label, value) tuples.
        tooltips = tooltips.items()
    
    tooltips = list(tooltips)  # Coerce to list from *args tuple, or .items().
    if len(tooltips) == 1 and simplify:
        # Just use the tooltip string without a tabular label.
        _, tooltips = tooltips[0]
    
    hover_tool = HoverTool(
        tooltips=tooltips,
        renderers=renderers,
        **kwargs
    )

    fig.add_tools(hover_tool)
    return hover_tool


# In[25]:


# App helper functions that should be moved elsewhere.

def set_output_file(outfile, title):
    """
    Set Bokeh output file for standalone application
    
    Filename suffix is coerced to 'html'
    
    Examples
    --------
    set_output_file(args.save or args.datafile, "OPH by industry")
    """
    
    outfile = Path(outfile).with_suffix(".html").as_posix()
    output_file(outfile, title=title, mode='inline')

def unpack_data_varnames(args, arg_names, defaults=None):
    """
    Look up command line arguments or defaults
    """
    
    # Assemble CL arguments, which default to None.
    mapping = {arg: getattr(args, arg) for arg in arg_names}
    if (defaults is not None
        and all(arg is None for arg in mapping.values())):
        # Use default names.
        mapping = dict(zip(arg_names, defaults))
        if len(defaults) > len(arg_names):
            # Heap extra defaults into last key.
            mapping[arg_names[-1]] = defaults[len(arg_names):]
    return mapping

def date_tuples(dates, length_threshold = np.inf):
    """
    Coerce monthly, quarterly, or annual dates to tuples
    
    Tuples (if converted to a list) are suitable for `bokeh` categorical axis
    
    Parameters
    dates : Series of str
        Dates which may be annual ('2021'), quarterly ('2021 Q3'), or
        monthly ('March 2021' or anything recognised by Pandas 
        `.to_period()`).
    length_threshold : integer, default np.inf
        If the number of unique `dates` exceeds this threshold, only the
        last two digits of years are used.  The default is to always
        use four-digit years.  If 0 is given, only the last two digits
        of years will be used, regardless of how many different `dates`
        there are.
    """
    
    sample_date = dates[0]
    n_dates = len(dates.unique())
    
    if re.fullmatch("\d{4}", sample_date):
        # Annual like '2019', use as is.
        if n_dates > length_threshold:
            # Keep only last two digits of year.
            tdate = [year[-2:] for year in dates]
        else:
            tdate = list(dates)
        return tdate

    if re.fullmatch("\d{4} ?Q\d", sample_date.upper()):
        # Quarterly like '2019Q3' or '2019 Q3'.
        # Wrap in a tuple for Bokeh categorical axis.
        tdate = dates.str.split(" ").apply(tuple)
    else:
        # Maybe monthly will work.
        # Create canonical (year, Mmm) category via datetime.
        dt_dates = pd.to_datetime(dates).dt.to_period("M")
        tdate = list(zip(dt_dates.dt.year.astype(str), dt_dates.dt.month.apply('M{:02d}'.format)))
        
    if n_dates > length_threshold:
        # Keep only last two digits of year.
        tdate = [(year[-2:], _) for (year, _) in tdate]
    return tdate

def filter_widget(options, title=None, start_value="first"):
    """
    Make a widget to select among values of a sequence
    """

    if title is None:
        try:
            title = options.name
        except AttributeError:
            title = "option"
    # Get unique options into a list, respecting order of appearance.
    options = list(pd.Series(options).unique())
    widget = SlideSelect(options=options,
                         title=title,  # Shown.
                         name=title + "_filter")  # Internal.
    if start_value == "last":
        widget.value = widget.options[-1]  # Start at last value.

    return widget

