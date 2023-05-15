"""
Make horizontal bar chart of productivity growth components by split factor

Functions
---------
figprodgrowsnap
    Make Bokeh Figure showing productivity growth components by split factor
"""

#%%
# Bokeh imports.
from bokeh import palettes

# Internal imports.
from ..base import iv_dv_figure
from ..snapcomp  import components_figure, link_widget_to_snapcomp_figure

#%%

def figprodgrowsnap(data, 
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
    Make snapshot horizontal bar chart of productivity growth components
    
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
