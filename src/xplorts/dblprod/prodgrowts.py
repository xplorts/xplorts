"""
Make vertical bar time series chart of productivity, GVA and labour growth

Functions
---------
figprodgrowts
    Make Bokeh Figure showing productivity, GVA and labour levels
"""

#%%
# Bokeh imports.
from bokeh import palettes

# Internal imports.
from ..base import iv_dv_figure
from ..dutils import date_tuples
from ..tscomp import link_widget_to_tscomp_figure, ts_components_figure

#%%

# Suppress quarterly or monthly axis labels for time series longer than this.
DATE_THRESHOLD = 40


def figprodgrowts(data,
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
    datevar = date
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
