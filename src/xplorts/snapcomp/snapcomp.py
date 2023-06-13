"""
Make standalone interactive chart showing snapshot components and total


Functions
---------
components_figure
    Interactive chart showing snapshot components and total by split group

link_widget_to_snapcomp_figure
    Link a select widget to components to show one level of split group
"""

#%%

from bokeh.models import ColumnDataSource

from ..base import (add_hover_tool, factor_view, link_widgets_to_groupfilters)
from ..scatter import grouped_scatter
from ..stacks import grouped_stack

#%%

def components_figure(
    fig,
    data,
    y,
    bar_variables,
    by=None,
    marker_variable=None,
    scatter_args={},
    bar_args={},
):
    """
    Interactive chart showing snapshot components and total by split group
    """

    source = ColumnDataSource(data)
    view_by_factor = factor_view(source, by)

    # Make scatter chart first, for sake of legend.
    markers = grouped_scatter(
        fig,
        iv_axis="y",
        iv_variable=y,
        marker_variable=marker_variable,
        source=source,
        view=view_by_factor,
        **scatter_args
    )
    fig._scatter = [markers]

    # Make stacked bars showing components.
    tooltips = ([] if marker_variable is None
                else
                    # Show value of line, regardless.
                    [(marker_variable, f"@{marker_variable}{{0,0.0}}")]
               )
    bars = grouped_stack(
        fig,
        iv_axis="y",
        iv_variable=y,
        bar_variables=bar_variables,
        source=source,
        view=view_by_factor,
        #tooltips=tooltips,
        **bar_args,
    )
    fig._stacked = bars

    ## Define hover info for whole figure.
    if isinstance(y, dict):
        iv_hover_variable = y["hover"]
    else:
        iv_hover_variable = y

    tooltips = [(by, f"@{{{by}}}"),
                (iv_hover_variable, f"@{{{iv_hover_variable}}}")]
    if marker_variable is not None:
        tooltips.append(
            (marker_variable, f"@{{{marker_variable}}}{{0[.]0 a}}")
        )
    tooltips.extend((bar, f"@{{{bar}}}{{0[.]0 a}}") for bar in bar_variables)

    hover = add_hover_tool(fig,
                           bars[0:1],  # Show tips just once for the stack, not for every glyph.
                           *tooltips,
                           name="Hover bar stack",
                           description="Hover bar stack",
                           mode="hline",
                           point_policy = 'follow_mouse',
                           attachment="vertical",
                           show_arrow = False,
                          )

    if fig.toolbar.active_inspect == "auto":
        # Activate just the new hover tool.
        fig.toolbar.active_inspect = hover
    else:
        # Add the new hover to list of active inspectors.
        fig.toolbar.active_inspect = fig.toolbar.active_inspect.append(hover)

    return [markers] + bars

#%%

def link_widget_to_snapcomp_figure(widget, fig=None, renderers=None):
    if renderers is None:
        # Use first set of stacked bars.
        sample = fig._stacked[0]
    elif isinstance(renderers, list):
        # Use first renderer.
        sample = renderers[0]
    else:
        # Assume we have a single renderer.
        sample = renderers

    # Get .filter attribute (newer bokeh) or .filters (pre bokeh 3.0).
    view = sample.view
    filter = getattr(view, "filter", None)
    filters = [filter] if filter is not None else view.filters

    for cds_filter in filters:
        # Sync filter to widget.
        cds_filter.group = widget.value
    # Sync groupfilters to widget (for multi-lines?).
    link_widgets_to_groupfilters(widget,
                                 source=sample.data_source,
                                 filter=filters)
