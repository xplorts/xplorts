"""
Make standalone interactive heatmaps for categorical time series data

Functions
---------
figheatmap
    Make a heatmap figure, with color bar

addheatmap
    Add a heatmap to a figure, with color map and hover tooltip.

jscb_set_from_selection
    Set object's .value dynamically in the browser from a source selection

ts_categorical_figure
    Make empty bokeh Figure with time series x and categorical y axis

"""
# See https://docs.bokeh.org/en/latest/docs/user_guide/topics/categorical.html#heatmaps


#%%

from math import pi
import pandas as pd

from bokeh.models import (BasicTicker, ColumnDataSource, CustomJS, FactorRange)
from bokeh.plotting import figure
from bokeh.transform import linear_cmap, log_cmap

## Imports from this package
from ..base import tf_margins_only
from ..dutils import date_tuples

#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40

#%%

# Make a FactorRange from categorical scalars or tuples, with uniform padding.
def _simple_factor_range(factor_values, *, padding=0.2, reverse=False):
    axis_range = pd.Series(factor_values).unique()  # Do not sort.
    if reverse:
        axis_range = list(reversed(axis_range))
    return FactorRange(factors=axis_range,
                       factor_padding = padding,
                       group_padding = padding,
                       subgroup_padding = padding)

#%%

def ts_categorical_figure(data,
            x,
            y,
            values,
            *,
            x_hover=None,
            title="(untitled)",
            suppress_factors=False,
            **kwargs):
    """
    Make empty bokeh Figure with time series x and categorical y axis

    Parameters
    ----------
    data: dict, DataFrame, or ColumnDataSource
        Data, including x, y, and values.
    x: str
        Name of data variable specifying date values for the horizontal
        axis.
    y: str
        Name of data variable specifying categorical values for the vertical
        axis.
    values: str
        Name of data variable specifying numerical values for each combination
        of x and y.
    x_hover: str, optional
        Name of data variable specifying pretty x values to display in hover
        tool.  If not given, x will be used.
    title: str
        Title to display above figure.
    suppress_factors: bool, default False
        X axis tick labels omit lowest level from hierarchical tuple
        categories, which are only displayed for the first and last ticks.
        For example, if x values are like (2021, "Q1"), the years would be
        shown but the quarters would mostly be suppressed to reduce clutter.
    kwargs
        Passed to bokeh.plotting.figure().

    Returns
    -------
    Bokeh Figure
    """

    # Convert data to CDS if necessary.
    if isinstance(data, (dict, pd.DataFrame)):
        source = ColumnDataSource(data)
    else:
        # Use presumed ColumnDataSource directly.
        source = data

    # Define categories for horizontal time axis.
    x_range = _simple_factor_range(source.data[x], padding=0)

    # Define categories for vertical axis.
    y_range = _simple_factor_range(source.data[y], reverse=True)

    # TOOLS = "hover,tap,save,pan,box_zoom,reset,xwheel_pan,xwheel_zoom,ywheel_pan,ywheel_zoom"
    TOOLS = "hover,tap,save,pan,box_zoom,reset,wheel_zoom"

    if x_hover is None:
        x_hover = x
    tooltips = tooltips=[(f'{y}', f'@{y}'),
                      (f'{x_hover}', f'@{x_hover}'),
                      (f'{values}', f'@{values}')]

    fopts = dict(
        title=title,
        x_range=x_range,
        y_range=y_range,
        x_axis_location="above",
        #width=900, height=400,
        tools=TOOLS, toolbar_location='below',
        tooltips=tooltips,
        )
    fopts.update(kwargs)

    fig = figure(**fopts)
    fig.toolbar.logo = None  # Hide bokeh logo.

    fig.grid.grid_line_color = None

    axis = fig.axis
    axis.axis_line_color = None
    axis.major_tick_line_color = None
    axis.major_label_text_font_size = "9px"
    axis.major_label_standoff = 0

    if suppress_factors:
        # Suppress most lowest level categorical tick labels.
        # If tick labels are tuples, higher levels will be displayed
        # as normal.
        fig.xaxis[0].formatter = tf_margins_only
    elif len(x_range.factors) > 10:
        # Rotate labels to reduce crowding
        fig.xaxis.major_label_orientation = pi / 3

    # Arrange for tap to select one cell of the figure source data.
    # fig.select(type=TapTool)

    return fig

#%%

# Apply a color mapper.
def _color_mapper(source, values, *, mapper=None, palette=None,
                  **kwargs):
    if palette is None:
        palette = "Viridis256"

    data = pd.Series(source.data[values])
    if mapper == "symmetric":
        high = data.abs().max()
        low = -high
    else:
        low, high = data.min(), data.max()

    # Avoid degenerate range of values.
    if low == high:
        if high < 0:
            high = 0  # low..0
        elif low > 0:
            low = 0  # 0..high
        else:
            high = 1  # 0..1

    if mapper in [None, "linear", "symmetric"]:
        mapper = linear_cmap
    elif mapper == "log":
        mapper = log_cmap

    color_map = mapper(values, palette,
                        low=low,
                        high=high,
                        nan_color=kwargs.pop("nan_color", "white"),
                        **kwargs)
    return color_map


def addheatmap(fig,
            data,
            x,
            y,
            values,
            *,
            color_map=None,
            palette=None,
            mapper=None,
            **kwargs):
    """
    Make interactive heatmap of categorical data

    Parameters
    ----------
    fig: Bokeh Figure
        Glyph rectangles are added to the figure to create a heatmap.
    data: dict, DataFrame, or ColumnDataSource
        Data, including x, y, and values.
    x: str
        Name of data variable specifying date values for the horizontal
        axis.
    y: str
        Name of data variable specifying categorical values for the vertical
        axis.
    values: str
        Name of data variable specifying numerical values for each combination
        of x and y.
    color_map: Bokeh color map, optional
        Maps data values to colors.  If not given, a linear_cmap will be
        created.
    palette: Bokeh color palette, default "Viridis256"
        Used to create a color map.  Ignored if color_map is specified.
    mapper: "linear", "log", or callable
        Used to create a color map.  Ignored if color_map is specified.
    kwargs
        Passed to fig.rect().

    Returns
    -------
    Bokeh Figure
    """

    # Convert data to CDS if necessary.
    if isinstance(data, (dict, pd.DataFrame)):
        source = ColumnDataSource(data)
    else:
        # Use presumed ColumnDataSource directly.
        source = data

    if color_map is None:
        color_map = _color_mapper(source, values,
                                  palette=palette,
                                  mapper=mapper)

    r = fig.rect(x=x, y=y, width=1, height=1, source=source,
               fill_color=color_map,
               line_color=None,
               nonselection_alpha=0.5,
               **kwargs,
               )

    return r

#%%

def figheatmap(data,
            x,
            y,
            values,
            *,
            title="(untitled)",
            x_widget=None, y_widget=None,
            figure_options={},
            bar_options={},
            **kwargs):
    """
    Make a heatmap figure, with color bar

    Parameters
    ----------
    data: dict, DataFrame, or ColumnDataSource
        Data, including x, y, and values.
    x: str
        Name of data variable specifying date values for the horizontal
        axis.
    y: str
        Name of data variable specifying categorical values for the vertical
        axis.
    values: str
        Name of data variable specifying numerical values for each combination
        of x and y.
    title: str, optional
        Title to display above figure.  The default is "(untitled)".
    x_widget : Bokeh widget, optional
        Tapping on the heatmap sets the .value property of this widget to
        the x coordinate of the selected (tapped) cell.
    y_widget : Bokeh widget, optional
        Tapping on the heatmap sets the .value property of this widget to
        the y coordinate of the selected (tapped) cell.
    figure_options : dict, optional
        Passed as keyword arguments to bokeh.plotting.fig().
    bar_options : dict, optional
        Passed as keyword arguments to ColorBar().
    **kwargs
        Keyword arguments for Figure.rect().

    Returns
    -------
    fig : bokeh.plotting.Figure
        Heatmap figure.
    """

    # Convert data to CDS if necessary.
    if isinstance(data, (dict, pd.DataFrame)):
        source = ColumnDataSource(data)
    else:
        # Use presumed ColumnDataSource directly.
        source = data

    # Transform monthly and quarterly dates to nested categories.
    source.data["_date_factor"] = date_tuples(source.data[x],
                                             length_threshold=DATE_THRESHOLD)

    # Prepare to suppress most quarters or months on axis if lots of them.
    n_dates = len(pd.unique(source.data[x]))
    suppress_factors = n_dates > DATE_THRESHOLD

    # growth_source = fig_growth_snapshot.select(StackUp)[0].source
    fig = ts_categorical_figure(
            source,
            x="_date_factor",  # Use tuple dates on figure axis.
            y=y,
            values=values,
            x_hover = x,  # Use original x dates for hover info.
            suppress_factors=suppress_factors,
            title=title,
            **figure_options
        )
    fig.y_range.bounds = "auto"  # Limit pan to actual categories.

    hm_rect = addheatmap(
            fig,
            source,
            x="_date_factor",
            y=y,
            values=values,
            **kwargs
        )

    color_bar = hm_rect.construct_color_bar(
        major_label_text_font_size="8px",
        # ticker=BasicTicker(#desired_num_ticks=len(palette)
        #                    ),
        #formatter=PrintfTickFormatter(format="%d%%"),
        label_standoff=6,
        border_line_color=None,
        padding=5,
        **bar_options,
    )

    fig.add_layout(color_bar, 'right')

    if x_widget is not None:
        jscb_set_from_selection(x_widget,
                                source=source,
                                column=x)

    if y_widget is not None:
        jscb_set_from_selection(y_widget,
                                source=source,
                                column=y)

    return fig

#%%

_JSCB_SET_FROM_LAST_SELECTED = """
    // Set .value property from last selected index a data source.
    /* args
        tgt: Object whose .value property will be assigned a value from
            `source[column]` in the last selected row of the data source.
        source: ColumnDataSource
        column: Name of column supplying potential target values
    */
    var indices = source.selected.indices;
    if (indices.length) {
        var last_selected_index = indices[indices.length - 1];
        var new_value = source.data[column][last_selected_index];
        tgt.value = new_value;
        console.log("Updating " + (tgt.name || "unnamed target"),
                    new_value);
    }
    """

def jscb_set_from_selection(obj, source, column):
    """
    Set object's .value dynamically in the browser from a source selection

    Arguments
    ---------
    tgt: Bokeh object
        The object's .value property will be assigned from `source[column]`,
        indexed by the last of the source's selected indices.
    source: ColumnDataSource
    column: str
        Name of column supplying potential values for the target.

    Returns
    -------
    None

    Side effects
    ------------
    Sets a CustomJS callback to trigger when source's selection changes.
    """
    callback = CustomJS(args={"tgt": obj,
                              "source": source,
                              "column": column},
                        code=_JSCB_SET_FROM_LAST_SELECTED)
    source.selected.js_on_change('indices', callback)

