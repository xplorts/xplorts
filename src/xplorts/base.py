"""
base
----
Miscellaneous helpers for interactive time series charts

Functions
---------
add_hover_tool
    Create a hover tool and add it to a Bokeh figure

extend_legend_items
    Create legend items and add to a Bokeh figure's legend

factor_filters
    Create GroupFilter objects for specified variables

factor_view
    Return a CDSView to filter source on specified variables

filter_widget
    Make a SlideSelect widget to select among values of a sequence

iv_dv_figure
    Create a Bokeh Figure with a horizontal or vertical independent axis

link_widgets_to_groupfilters
    Link values of widgets to corresponding GroupFilter objects

set_output_file
    Set Bokeh output file for standalone application

unpack_data_varnames
    Look up command line arguments or defaults

variables_cmap
    Map variable names to colors
"""

#%%

from bokeh import palettes
from bokeh.io import output_file
from bokeh.models import (CDSView, ColumnDataSource, CustomJS, GroupFilter, FactorRange,
                          HoverTool, Legend, LegendItem)
from bokeh.models import formatters as bk_formatters
#from bokeh.models.formatters import FuncTickFormatter
from bokeh.plotting import figure
from bokeh.util.warnings import BokehDeprecationWarning

import functools
import operator

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime
from pathlib import Path

import warnings

# Imports from this package.
from xplorts.dutils import dict_fill
from xplorts.slideselect import SlideSelect

#%%

# Use CustomJSTickFormatter for newer bokeh, or
# FuncTickFormatter for older bokeh.
def _custom_tick_formatter(code):
    try:
        cls = bk_formatters.CustomJSTickFormatter
    except AttributeError:
        cls = bk_formatters.FuncTickFormatter
    return cls(code=code)



# Tick formatter to suppress most lowest level categorical tick labels.
# If tick labels are tuples, higher levels will be displayed
# as normal.
tf_margins_only = _custom_tick_formatter(
    code="""
    if ((index == 0) | (index == ticks.length - 1)) {
        return tick;
    } else {
        return '';
    }
    """
)


#%%

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
    """

    if isinstance(by, str):
        # Wrap in list, for convenience.
        by = [by]

    if not isinstance(by, dict):
        # Map `by` variables to initial values to use in filter.
        is_cds = isinstance(source, ColumnDataSource)
        data = (source.data if is_cds else source)
        # Use first value of each variable named by `by`.
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

    # Get list of one or more filters.
    filters = factor_filters(by, source=source, **kwargs)
    with warnings.catch_warnings():
        # Catch deprecations from bokeh CDSView if necessary.
        warnings.simplefilter("error")
        try:
            # Use legacy call with gratuitous CDSView.source property.
            view = CDSView(
                source=source,
                filters=filters
            )
        except (AttributeError, BokehDeprecationWarning):
            # Use newer call without CDSView.source property.
            if len(filters):
                if len(filters) == 1:
                    # use the single filter as is.
                    filter = filters[0]
                else:
                    # Combine multiple filters with logical `and`.
                    filter = functools.reduce(operator.and_, filters)

                view = CDSView(filter=filter)
            else:
                # No filters to apply.
                view = CDSView()

    return view


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

def iv_dv_figure(
    iv_data = None,
    iv_axis = "x",
    legend = "default",
    legend_place = "center",
    suppress_factors = False,
    **kwargs
):
    """
    Make empty bokeh Figure with one categorical axis and one continuous axis

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


def link_widgets_to_groupfilters(widgets, source, filter):
    """
    Link values of widgets to corresponding GroupFilter objects

    Parameters
    ----------
    widgets : Bokeh widget or list of widgets
        The `value` property of each widget will be linked to the
        `group` property of the corresponding `GroupFilter`.  If there are
        more widgets than filters, the excess widgets are ignored.
    source : ColumnDataSource
        Data source, which will be configured to emit a change signal when
        a filter's `group` property changes, to re-render the relevant figure.
    filter : GroupFilter or sequence of GroupFilter
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
                                 source=source,
                                 filter=view_by_factor.filters)
    """

    # Wrap singleton widget or filter, for convenience.
    if not isinstance(widgets, (list, tuple)):
        widgets = [widgets]
    if not isinstance(filter, (list, tuple)):
        filter = [filter]

    for widget, filt in zip(widgets, filter):
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
