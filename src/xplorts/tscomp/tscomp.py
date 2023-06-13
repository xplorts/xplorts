"""
tscomp
------
Make standalone interactive chart showing time series components and total.


Functions
---------
ts_components_figure
    Interactive chart showing time series components and total by split group

link_widget_to_tscomp_figure
    Link a select widget to components series to show one level of split group
"""

#%%
from bokeh.models import ColumnDataSource

## Imports from this package
from ..base import (add_hover_tool, factor_view,
                          link_widgets_to_groupfilters)
from ..lines import grouped_multi_lines, link_widget_to_lines
from ..stacks import grouped_stack

#%%
def ts_components_figure(
    fig,
    data,
    date_variable,
    bar_variables,
    by=None,
    line_variable=None,
    line_args={},
    bar_args={},
):
    """
    Interactive chart showing time series components and total by split group

    Parameters
    ----------
    date_variable: str or dict
        If str, the name of a data column, which will be shown on the horizontal
        axis.

        If dict, should map key "plot" to a variable to show on the
        horizontal axis and should map key "hover" to a corresponding variable
        to display in hover information.  This is often useful when displaying
        quarterly dates as nested categories like `("2020", "Q1")`.

    """

    # Make line chart first, for sake of legend.
    lines = grouped_multi_lines(
        fig,
        data,
        iv_variable=date_variable,
        data_variables=line_variable,
        by=by,
        **line_args
    )

    source = ColumnDataSource(data)
    view_by_factor = factor_view(source, by)

    # Make stacked bars showing components.
    bars = grouped_stack(
        fig,
        iv_axis="x",
        iv_variable=date_variable,
        bar_variables=bar_variables,
        source=source,
        view=view_by_factor,
        **bar_args,
    )

    ## Define hover info for whole figure.
    if isinstance(date_variable, dict):
        iv_hover_variable = date_variable["hover"]
    else:
        iv_hover_variable = date_variable

    tooltips = [(by, f"@{{{by}}}"),
                (iv_hover_variable, f"@{{{iv_hover_variable}}}")]
    if line_variable is not None:
        tooltips.append(
            (line_variable, f"@{{{line_variable}}}{{0[.]0 a}}")
        )
    tooltips.extend((bar, f"@{{{bar}}}{{0[.]0 a}}") for bar in bar_variables)

    hover = add_hover_tool(fig,
                           bars[0:1],  # Show tips just once for the stack, not for every glyph.
                           *tooltips,
                           name="Hover bar stack",
                           description="Hover bar stack",
                           mode="vline",
                           point_policy = 'follow_mouse',
                           attachment="horizontal",
                           show_arrow = False,
                          )

    if fig.toolbar.active_inspect == "auto":
        # Activate just the new hover tool.
        fig.toolbar.active_inspect = hover
    else:
        # Add the new hover to list of active inspectors.
        fig.toolbar.active_inspect = fig.toolbar.active_inspect.append(hover)

    fig._lines = lines
    fig._stacked = bars

    return lines + bars

#%%
def link_widget_to_tscomp_figure(widget, fig=None, lines=None, bars=None):
    """

    """
    if lines is None:
        lines = fig._lines
    if bars is None:
        bars = fig._stacked
    source = bars[0].data_source
    view = bars[0].view
    # Get .filter attribute (newer bokeh) or .filters (pre bokeh 3.0).
    filter = getattr(view, "filter", None) or view.filters

    link_widget_to_lines(widget, lines)
    link_widgets_to_groupfilters(widget,
                                 source=source,
                                 filter=filter)
