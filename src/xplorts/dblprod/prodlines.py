"""
Make multi-line time series chart of productivity, GVA and labour levels

Functions
---------
figprodlines
    Make Bokeh Figure showing productivity, GVA and labour levels
"""

#%%
# Bokeh imports.
from bokeh import palettes

# Internal imports.
from ..base import iv_dv_figure
from ..dutils import date_tuples
from ..lines import grouped_multi_lines, link_widget_to_lines

#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40


def figprodlines(data, 
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
