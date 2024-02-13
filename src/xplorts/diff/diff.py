import copy
import numpy as np
import pandas as pd

from functools import partial

from bokeh.colors import named as colors
from bokeh.io import show
from bokeh.layouts import column, grid, layout, row
from bokeh.models import (ColumnDataSource, CustomJSTransform, FixedTicker,
                          TabPanel, Tabs)
from bokeh.models.widgets import Div
from bokeh.palettes import diverging_palette, interp_palette
from bokeh.transform import linear_cmap


# import xplorts stuff
from xplorts.heatmap import heatmap as hm
from xplorts.growthcomps import growth_vars
from xplorts.lines import link_widget_to_lines

#%%

DIFF_KEYS = ["original", "new"]


# # Return index of midpoint of sequence.
# def _midpoint(seq):
#     n = (len(seq) + 1) // 2
#     return n

# # Return copy of sequence, with middle item or two set to specified value.
# def _zap_middle(seq, val):
#     result = seq[:]  # shallow copy
#     mid = _midpoint(result)
#     result[mid] = val
#     if len(result) % 2 == 1:
#         # Zap next item too for even-length sequence.
#         result[mid + 1] = val
#     return result

# _CC_CYCLIC_GREY = cc.b_cyclic_grey_15_85_c0_s25
# _CC_DIVERGING_RED_BLACK = list(reversed(cc.b_diverging_bwr_20_95_c54))

# DEFAULT_PALETTE_ABS = _zap_middle(_CC_CYCLIC_GREY, "white")  # Positive/negative same colour.

# DEFAULT_PALETTE_POS_NEG = _zap_middle(_CC_DIVERGING_RED_BLACK, "white")


_NAN_COLOR = "linen"
_ZERO_COLOR = "white"

## Make red-white-blue diverging palette for neg-zero-pos values.
RWB_PALETTE_POS_NEG = diverging_palette(
    interp_palette([colors.darkred.to_hex(), colors.white.to_hex()], 128),
    interp_palette([colors.darkblue.to_hex(), colors.white.to_hex()], 128),
    256
    )

## Make categorical gray symmetric palette for -5.25 to +5.25.
_GRAY_SMALL_COLOR = "gainsboro"
_GRAY_MODERATE_COLOR = "darkgray"
_GRAY_BIG_COLOR = "darkslategray"

_GRAY_POS_PALETTE = (
    [_ZERO_COLOR]  # 0 to 0.05
    + [_GRAY_SMALL_COLOR] * 19  # 0.05 to 1
    + [_GRAY_MODERATE_COLOR] * 80  # 1 to 5
    + [_GRAY_BIG_COLOR] * 5  # 5+ %
)

PALETTE_ABS_CAT_GRAY = list(reversed(_GRAY_POS_PALETTE)) + _GRAY_POS_PALETTE

_GRAY_TICKS = [-5, -1, 0, 1, 5]

#%%

class RevisedTS():
    """
    Time series dataset along with an earlier vintage

    The vintage `new` represents current values for all time periods.  The
    vintage `original` represeents a snapshot of previous values for all
    time periods that were available then.

    One of the two vintages can be accessed directly through an instance
    `revts` in several ways:
        # As an instance property
        revts.new  # DataFrame, current values for all time periods
        revts.original  # DataFrame, earlier values for all time periods

        # As a key-value mapping
        revts[vintage]  # For vintage in ["new", "original"]

        # Via `.get()`
        revts.get(vintage, default)  # For vintage in ["new", "original"]

    Instances are iterable, yielding a sequence of vintage names
    ["new", "original"].

    Methods
    -------
    apply()
        Apply a function to each vintage dataset.

    calc_growth()
        Calculate growth rates for measures in each vintage.

    get()
        Get specified vintage dataset.

    revisions()
        Calculate revisions in new data compared to original data.


    Instance attributes
    -------------------
    all_measures: [str, ...]
        Includes all of `.levels`, `.indexes` and `.growths`.  Read only.

    by: str, [str, ...]
        Columns representing categorical split levels.  A well-formed time
        series dataset will have at most one row for each `date` value for
        each combination of `by` values.

    data: dict
        Maps vintage keys "new" and "original" to dataframes.

    date: str
        Name of dataframe column representing time periods.

    growths: [str, ...]
        Columns representing growth series (?).

    indexes: [str, ...]
        Columns representing index series that allow meaningful assessment of
        growth rates from one time period to another, but not comparison of
        relative revisions across vintages.

    levels: [str, ...]
        Columns representing measurement quantities that allow meaningful
        comparison of relative revisions across vintages--generally not
        index series or growths.

    new: DataFrame, None
        Current vintage of time series dataset.

    original: DataFrame, None
        Previous vintage of time series dataset.
    """
    data = None
    date = None
    by = None

    def __new__(cls, *args, **kwargs):
        if args:
            data, *more_args = args
            if more_args:
                raise ValueError("Too many positional arguments, only one allowed")
            if isinstance(data, RevisedTS):
                # Use existing object as template for new object.
                obj = copy.copy(data)
                obj.data = None  # Make new .data dict in __init__().
                obj.__class__ = cls
                return obj
        obj = super().__new__(cls)
        # Make (mutable) levels and indexes placeholders for each object.
        obj.levels = []
        obj.indexes = []
        obj.growths = []
        return obj


    def __init__(self, data, *, date=None,
                 original=None, by=None,
                 indexes=None, levels=None, growths=None):
        """
        Time series dataset along with an earlier vintage

        Parameters
        ----------
        data : DataFrame, RevisedTS, dict
            Current vintage of data.  May also provide an earlier vintage
            in a RevisedTS or dict object.

            If `dict`, the key "new" should map to a DataFrame representing
            the current vintage, the optional key "original" may also map to
            a DataFrame (or `None`) representing an earlier vintage, and any
            other keys are ignored.
        date : str
            Name of data column representing time periods of time series data.
        original : DataFrame, optional
            Earlier vintage of data.

            If `data` is a RevisedTS or `dict`
            and a DataFrame is specified through the `original` keyword
            parameter, the keyword parameter takes precedence over
            `data["original"]`.

            If the `original` keyword parameter is None (the default),
            `data["original"]` is retained as is.
        by : str, optional
            Name of data column representing categorical splits of each time
            series. The default is None.
        indexes : str or list, optional
            Name or list of names of data columns containing index-like data.
            These columns will be displayed in heatmaps showing growth,
            but not in the heatmap showing time series levels.  The default
            is None.
        levels : str or list, optional
            Name or list of names of data columns containing time series
            levels.  These columns will be displayed in a heatmap showing
            levels as well as in heatmaps showing growth rates.  The default
            is None.

        Returns
        -------
        None.

        """
        if isinstance(data, (RevisedTS, dict)):
            self.data = {
                "new": data["new"],
                "original": data.get("original", None)
            }
        else:
            self.data = {
                "new": data,
                "original": None
            }

        if original is not None:
            # Set original, overriding existing .original if necessary.
            self.original = original

        if not isinstance(data, RevisedTS):
            if indexes is None and levels is None:
                # Use all columns other than `date` and `by`.
                levels = [col for col in self.new.columns
                          if col != date and col != by]

        if levels is not None:
            self.levels = levels

        if indexes is not None:
            self.indexes = indexes

        if growths is not None:
            self.growths = growths

        if (len(self.levels) + len(self.indexes) + len(self.growths)
            != len(self.levels + self.indexes + self.growths)):
                raise ValueError(
                    "Levels, indexes and growths must use different columns")

        self.date = date
        self.by = by

    # Allow iteration over the parent object, delegating it to .data.
    # `list(RevisedTS(...))` is thus the same as `list(RevisedTS(...).data)`,
    # giving `["new", "original"]`.
    def __iter__(self):
        yield from self.data

    @property
    def all_measures(self):
        """All items in `.levels`, `.indexes` and `.growths`.  Read only."""
        return self.levels + self.indexes + self.growths

    @property
    def new(self):
        """Current vintage of time series dataset."""
        return self.data["new"]

    @new.setter
    def new(self, data):
        self.data["new"] = data

    @property
    def original(self):
        """Previous vintage of time series dataset."""
        return self.data["original"]

    @original.setter
    def original(self, data):
        self.data["original"] = data

    ## Methods

    def get(self, *args):
        """Get specified vintage dataset."""
        return self.data.get(*args)

    # Allow read/write access via obj[key], like obj["new"].
    __getitem__ = get

    def __setitem__(self, key, value):
        self.data[key] = value


    def apply(self, fct, *args, **kwargs):
        """
        Apply a function to each vintage dataset.

        Parameters
        ----------
        fct : callable
            Function to apply.  Will be called as `fct(data, *args, **kwargs)`
            for each `data` from `self.new` and `self.original`.  Should
            return a DataFrame the same shape as `data`.
        *args
            Additional positional arguments.
        **kwargs
            Keyword arguments passed to `fct`.

        Returns
        -------
        result : RevisedTS
            Transformed data for each vintage.
        """
        result = RevisedTS(self)  # shallow copy
        result.__dict__.update(self.__dict__)  # copy properties
        result.data = {
            key: fct(self[key], *args, **kwargs)
            for key in DIFF_KEYS
            }
        return result


    def calc_growth(self, *args, **kwargs):
        """
        Calculate growth rates for measures in each vintage.

        Parameters
        ----------
        *args, **kwargs
            Passed to `growth_vars()` along with each vintage dataset.

        Returns
        -------
        result : RevisedTS
            Copy of original, replacing values in `.levels` and `indexes`
            columns with their corresponding growth rates.
        """
        result = self.apply(
            growth_vars,
            *args,
            columns=self.levels + self.indexes,
            date_var=kwargs.pop("date", self.date),
            by=kwargs.pop("by", self.by),
            **kwargs)
        result.growths = result.all_measures
        result.indexes = []
        result.levels = []
        return result


    # Calculate revisions of new data compared to original data.
    def revisions(self, **kwargs):
        """
        Calculate revisions in new data compared to original data.

        Compares columns in `.levels` and `.growths`, but not `.indexes`.

        Parameters
        ----------
        **kwargs
            Keyword arguments passed to `growth_vars()`.

        Returns
        -------
        result : DataFrame
            Time series dataset, same shape as `.new`.
        """
        result = growth_vars(
            self.new,
            baseline=self.original,
            by=self.by,
            date_var=self.date,
            columns=self.levels + self.growths,
            **kwargs)
        result[self.indexes] = pd.NA
        return result

#%%

def link_widget_to_heatmaps(widget, models):
    """Link a widget to .visible property of heatmap layouts"""
    return link_widget_to_lines(widget, models)


def revision_layout(
        data,
        *,
        x, y, values,
        title="Revisions",
        palette_dict={"posneg": None, "abs": None},
        visible=True,
        **kwargs
        ):
    """
    Row of two heatmaps showing signed revisions and absolute revisions.

    Parameters
    ----------
    data : DataFrame or ColumnDataSource
        Dataset of revision statistics.
    x : str
        Name of categorical column for horizontal heatmap axis.
    y : str
        Name of categorical column for vertical heatmap axis.
    values : str
        Name of quantitative column mapped to heatmap colour.
    title : str, optional
        Text to display above heatmaps. The default is "Revisions".
    palette_dict : dict, optional
        Override default color palettes.  If the key "posneg" is included, its
        value overrides the default palette for signed revisions.  If the key
        "abs" is included, its value overrides the default palette for
        absolute revisions.
    visible : bool, optional
        Make the layout visible. The default is True.  Used with widgets to
        interactively switch between heatmaps for different measures in a
        dataset.
    **kwargs
        Keyword arguments passed to `figheatmap()`.

    Returns
    -------
    Bokeh layout
        Visible or invisible row of two heatmaps that use a single
        ColumnDataSource.
    """
    palette_posneg = (palette_dict.get("posneg", None)
                      or RWB_PALETTE_POS_NEG)

    palette_abs = (palette_dict.get("abs", None)
                      or PALETTE_ABS_CAT_GRAY)

    # Make CDS to use in both heatmaps, with different palettes.
    source = (ColumnDataSource(data) if not isinstance(data, ColumnDataSource)
              else data)

    data_values = pd.Series(source.data[values])
    vmin = data_values.min()
    if pd.isna(vmin) or vmin > -5.25:
        vmin = -5.25
    vmax = data_values.max()
    if pd.isna(vmax) or vmax < 5.25:
        vmax = 5.25
    fig_pos_neg = hm.figheatmap(
        source,
        x=x,
        y=y,
        values=values,
        title="Revision %",
        # palette=palette_posneg,
        # mapper="symmetric",
        color_map = linear_cmap(values,
                                palette_posneg,
                                low=min(vmin, -vmax),
                                high=max(vmax, -vmin),
                                nan_color=_NAN_COLOR),
        )

    fig_abs = hm.figheatmap(
        source,
        x=x,
        y=y,
        values=values,
        title="Absolute revision %",
        # palette=palette_abs,
        color_map = linear_cmap(values,
                                palette_abs,
                                low=-5.25,
                                high=5.25,
                                # low_color=_GRAY_BIG_COLOR,
                                # high_color=_GRAY_BIG_COLOR,
                                nan_color=_NAN_COLOR),
        bar_options={
            "ticker": FixedTicker(ticks=_GRAY_TICKS)
        }

        # palette=PALETTE_ABS_CAT_GRAY,
        # mapper="symmetric",
        # high=np.sqrt(10),
        # low=np.sqrt(10),
        # high_color=_GRAY_BIG_COLOR,
        )
    return row(fig_pos_neg, fig_abs, visible=visible)


def revtab(
        data,
        *,
        x, y,
        values,
        title="Revisions",
        palette_dict={"posneg": None, "abs": None},
        **kwargs
        ):
    """
    Bokeh tab showing interactive revision heatmaps

    Parameters
    ----------
    data : DataFrame, ColumnDataSource
        Revision statistics.
    x : str
        Name of categorical column for horizontal heatmap axis.
    y : str
        Name of categorical column for vertical heatmap axis.
    values : str, widget
        Name of quantitative column to show using heatmap colours.  If a
        widget is given, heatmaps are created for each of its options,
        using the widget to select a single option at a time to be visible.
    title : str, optional
        Tab name to display. The default is "Revisions".
    palette_dict : dict, optional
        Override default color palettes.  If the key "posneg" is included, its
        value overrides the default palette for signed revisions.  If the key
        "abs" is included, its value overrides the default palette for
        absolute revisions.
    **kwargs
        Keyword arguments passed to `revision_layout()`.

    Returns
    -------
    tab : Bokeh TabPanel
        Shows revision heatmaps for one measure at a time.
    """
    if isinstance(values, str):
        # Prepare to show a single data measure.
        widget = None
        value_cols = [values]
    else:
        # Prepare to show any data measure selected by a widget.
        widget = values
        value_cols = widget.options

    heatmaps = [
        revision_layout(
            data,
            x=x,
            y=y,
            values=value_col,  # current column
            palette_dict=palette_dict,
            visible=False,  # Hide most data measures.
            **kwargs
        ) for value_col in value_cols]
    heatmaps[0].visible = True  # Show first data measure.

    if widget is not None:
        # Sync widget to .visible property of data measure heatmaps.
        link_widget_to_heatmaps(widget, heatmaps)

    tab_layout = (column(widget, *heatmaps) if widget is not None
                  else heatmaps[0])

    tab = TabPanel(
        title=title,
        child=tab_layout)
    return tab

#%%


# if __name__ == "__main__":
if False:
    data_original = pd.DataFrame.from_records(
        [(2010, "A", 100),
         (2011, "A", 110),
         (2012, "A", 90),
         (2013, "A", 95),

         (2010, "B", 100),
         (2011, "B", 95),
         (2012, "B", 110),
         (2013, "B", 95)],
        columns=["date", "industry", "gva"]
        )
    data_original["date"] = data_original["date"].astype(str)
    data_original["hours"] = data_original["gva"].values[::-1] * 1.1

    data_new = pd.DataFrame.from_records(
        [(2010, "A", 105),
         (2011, "A", 110),
         (2012, "A", 95),
         (2013, "A", 90),

         (2010, "B", 100),
         (2011, "B", 90),
         (2012, "B", 115),
         (2013, "B", 100)],
        columns=["date", "industry", "gva"]
        )
    data_new["date"] = data_new["date"].astype(str)
    data_new["hours"] = data_new["gva"].values[::-1] * 0.9

    data_rts = RevisedTS(
        data_new,
        original=data_original,
        date="date",
        by="industry",
        )

    tabs = revtab(data_rts)

    # Make app that shows tabs of various charts.
    app = layout([
        Div(text="<h1>" + "Revisions 'old' vs 'original'"),  # Show title as level 1 heading.
        tabs
        ])

    show(app)  # Save file and display in web browser.

