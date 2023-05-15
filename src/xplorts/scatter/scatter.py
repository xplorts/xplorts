"""
Make standalone interactive marker charts for categorical data

Functions
---------
grouped_scatter
    Add a scatter plot to a figure, with legend entry and hover tooltip.
"""

#%%

## Imports from this package
from ..base import (add_hover_tool, extend_legend_items)

#%%

def grouped_scatter(
    fig,
    iv_axis="x",  # axis for independent variable.
    iv_variable=None,
    marker_variable=None,
    marker="circle",
    tooltips=[],  # optional
    **kwargs  # Usually need `source` and `view` among these.
):
    """
    Add a scatter plot to a figure, with legend entry and hover tooltip
    
    Parameters
    ----------
    fig : Bokeh Figure
        A scatter glyph will be added to this figure.
    iv_axis : str, default "x"
        Either "x" or "y".  Defines the chart orientation, with a categorical independent 
        variable plotted along either the horizontal "x" axis, or the vertical "y" axis.
    iv_variable : str
        Name of data source column to plot along the `iv_axis`.
    marker_variable : str
        Dependent variable to plot against `iv_variable`.
    marker : str, default "circle"
        Shape to use for markers.  Passed to `Figure.scatter()`.
    tooltips : list
        Optional additional tooltips.
    kwargs : mapping
        Passed to `bokeh.plotting.figure.scatter()`.  Should normally map "source" to a
        `ColumnDataSource` and "view" to a `GroupView` object to achieve a chart
        that shows one level of a split factor at a time.
        
    Returns
    -------
    Bokeh renderer
    
    Examples
    --------
    from slideselect import SlideSelect

    ## Define a growth series, split by industry.
    df_growth = pd.DataFrame([
        (2001, 'A', 10),
        (2002, 'A', 5),
        (2003, 'A', -2),
        (2001, 'B', 3),
        (2002, 'B', 7),
        (2003, 'B', 4)
    ], columns=["date", "industry", "jobs"])
    source = ColumnDataSource(df_growth)

    # Make a widget to choose an industry to show.
    factor_levels = sorted(df_growth["industry"].unique())
    filter_widget = SlideSelect(options=factor_levels,
                                name="industry_filter")

    # Link the widget to a view showing one industry at a time.
    view_by_factor = factor_view(source, "industry")
    link_widgets_to_groupfilters(filter_widget, 
                                 view=view_by_factor)
    color_map = {"jobs": "chocolate"}
    fig = iv_dv_figure(
        iv_data = source.data["date"],
        iv_axis = "x",
    )

    vbars = grouped_scatter(fig, iv_axis="x", iv_variable="date", marker_variable="gva",
                            color_map=color_map, source=source, view=view_by_factor)

    # Show widget and chart.
    show(layout(
        [[filter_widget],
         [fig]])
    """

    assert iv_axis in "xy", f"iv_axis should be 'x' or 'y', not {iv_axis}"
    dv_axis = "xy".replace(iv_axis, "")  # axis for dependent variable.
    #dv_direction = "vertical" if iv_axis == "x" else "horizontal"

    if marker_variable in ("", []):
        # Return empty list of renderers.
        return []
    
    # Make scatter.
    scatter_defaults = {
        "size": 6,
        "alpha": 0.6,
        "hover_fill_alpha": 1.0,  # Highlight hovered marker.
    }
    markers = fig.scatter(
        **{
            iv_axis: iv_variable,
            dv_axis: marker_variable
        },
        name=marker_variable,
        marker=marker,
        **{**scatter_defaults, **kwargs}  # kwargs can override these defaults.
    )

    extend_legend_items(
        fig,
        {marker_variable: markers}
    )

    ## Define hover info for markers.
    # Show name of hovered variable, along with date and the value.
    tooltip = '$name @date: @$name{0,0.0}'
    
    add_hover_tool(fig, [markers], ("marker", tooltip), *tooltips)

    return markers
