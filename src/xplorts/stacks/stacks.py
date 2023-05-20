"""
Make standalone interactive stacked bar charts for categorical data


Functions
---------
grouped_stack()
    Add to a Figure bidirectional stacked bar charts with split factor
"""


## Imports from this package
from .bokeh_stacks import hbar_stack_updown, vbar_stack_updown

from ..base import extend_legend_items

#%%
def grouped_stack(
    fig,
    iv_axis="x",
    iv_variable=None,
    bar_variables=[],
    #tooltips=[],  # optional
    **kwargs  # Usually need `source` and `view` among these.
):
    """
    Grouped renderers for stacked bar charts with data that may be positive or negative
    
    Parameters
    ----------
    iv_variable: str or dict
        If str, the name of a data column, which will be shown on the horizontal
        axis.  
        
        If dict, should map key "plot" to a variable to show on the
        horizontal axis and should map key "hover" to a corresponding variable
        to display in hover information.  This is often useful when displaying
        quarterly dates as nested categories like `("2020", "Q1")`.    
    """

    assert iv_axis in "xy", f"iv_axis should be 'x' or 'y', not {iv_axis}"
    #dv_axis = "xy".replace(iv_axis, "")
    bar_direction = "vbars" if iv_axis == "x" else "hbars"
    bar_width_key = "width" if bar_direction=="vbars" else "height"
    
    if isinstance(iv_variable, dict):
        iv_plot_variable = iv_variable["plot"]
        #iv_hover_variable = iv_variable["hover"]
    else:
        iv_plot_variable = iv_variable
        #iv_hover_variable = iv_plot_variable

    stack_function = vbar_stack_updown if bar_direction=="vbars" else hbar_stack_updown
    
    if bar_variables == []:
        # Return empty list of renderers.
        return []
    
    bars = stack_function(
        fig,
        bar_variables,
        alpha=0.25,
        ## hover_fill_alpha=0.5,  # Highlight hovered set of bars (broken).
        **{iv_axis: iv_plot_variable},  # x= or y=.
        **{bar_width_key: 0.9},  # width= or height=.
        **kwargs,  # Usually include `source` and `view`.
    )

    extend_legend_items(
        fig,
        {var: bars[2*i] for i, var in enumerate(bar_variables)}
    )

    ## Define hover info for individual bars.
    # Show name of hovered bar, along with IV value and the bar value.
    #bar_tooltip = f'$name @{iv_hover_variable}: @$name{{0,0.0}}'
    
    #bar_hover = add_hover_tool(fig, bars, 
    #                           ("bars", bar_tooltip), 
    #                           *tooltips,
    #                           name="Hover individual bars",
    #                           description="Hover individual bars")

    return bars
