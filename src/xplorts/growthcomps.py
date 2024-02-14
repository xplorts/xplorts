"""
growthcomps.py

Tools for calculating growth of time series and their contribution to growth
of derived series.

Classes
-------
GrowthComponent
    Names a data column of time series values, and specifies weighting for the
    contribution of growth in this series to overall growth of some derived
    series.

SignReversedComponent
    Sub-class of GrowthComponent for special case when weighting is -1 (as
    for a factor in the denominator of a ratio).

Functions
---------
growth_vars
    Calculate growth for columns in a dataframe.

"""

import numpy as np
import pandas as pd

#from xplorts.dutils import growth_pct_from
from xplorts import dutils

#%%

class GrowthComponent:
    def __init__(self, name, cweight=1,
                 cname_format="{name}",
                 # cname=None, suffix=None,
                 ):
        """
        Instance of GrowthComponent

        Parameters
        ----------
        name : str
            Name of a data column that will provide time series values for
            this component of some dependent variable.
        cweight : (float, str), optional
            Multiplier to calculate how much growth in some dependent
            variable is produced by each percentage point of growth in this
            component. The default is 1.  Can name a data column if the
            component weight depends on other data.

            If the dependent variable is `y = num / den`, component `num`
            should have `cweight = 1` and component `den` should have
            `cweight = -1`.

            If the dependent variable is `y = a + b`, create
            weighting variables `w_a = a / (a + b)` and `w_b = b / (a + b)`,
            then specify component weight for `a` as `cweight = "w_a"` and
            for `b` as `cweight = "w_b"`.
        cname_format: str
            Format string to make name for weighted growth component.  If not
            given, '{name}' is used, so that the weighted growth component has
            the same name as the data column of level values.

        Returns
        -------
        None.

        """
        self.name = name
        self.cweight = cweight
        self.cname = cname_format.format(name=name)
        # self.cname = cname or "".join([name, suffix])

    def growth_component(self, data, baseline=None):
        """
        Calculate weighted growth component

        XX Must calculate at same time as growth, so that weighting variables
        can use base period GVACP, hshare, etc.  May need flexibility to
        allow different approaches to the weighting, e.g. use base period
        (which may itself be an annual average of quarters), or mid-point,
        or end-point weight.

        The `name` attribute of the component picks out a column of `data`,
        which is multiplied by the `cweight` attribute of the component.

        Parameters
        ----------
        data : Dataframe
            Must include a column matching the component's `name` attribute,
            which should contain growth rates.
        baseline : DataFrame, optional
            If the component's `cweight' is a string, then it can name a
            column in `baseline`.  Otherwise the cweight is coerced to a
            float.  If `baseline` is not specified, `data` is used.

        Returns
        -------
        component : Series
            Weighted growth component.
        """
        if baseline is None:
            baseline = data
        cweight = self.cweight
        if isinstance(cweight, str):
            if cweight in baseline.columns:
                # Use named column of other for cweight rather than a constant.
                cweight = baseline[cweight]
            else:
                # Coerce cweight to float.
                cweight = float(cweight)
        component = data[self.name] * cweight
        component.name = self.cname
        return component


class SignReversedComponent(GrowthComponent):
    def __init__(self, cname):
        """
        Instance of SignReversedComponent

        The instance is a GrowthComponent with attributes `self.cweight = -1`
        and `self.cname` calculated by concatenating " (sign reversed)" onto
        the end of `name`.

        Parameters
        ----------
        name : str
            Name of a data column that will provide time series values for
            this component of some dependent variable.

        Returns
        -------
        None.

        """

        super().__init__(cname, cweight=-1,
                         cname_format="{name} (sign reversed)")

#%%

# Compare dataframe columns to another dataframe.
def _df_compare(data, other, columns, *, method):
    # Copy original dataframe with nan in `columns`.
    result = data.assign(**{var: np.nan for var in columns})
    # Fill `columns` with result of comparison.
    result[columns] = dutils.compare(
        data[columns],
        other[columns],
        method=method)
    return result

# Compare dataframe columns, which may be given as Component objects.
def _df_weighted_diff(data, other, columns=None, *, method):
    if columns is None:
        columns = data.columns
    column_names = [getattr(col, "name", col) for col in columns]
    result = _df_compare(data, other, column_names, method=method)

    # Scale growth components by cweight.
    components = [col for col in columns if isinstance(col, GrowthComponent)]
    for component in components:
        # cweight = component.cweight
        # if isinstance(cweight, str):
        #     cweight = other[cweight]
        # result[component.name] *= cweight
        result[component.name] = component.growth_component(result, other)

    # Rename components.
    result.rename(columns={c.name: c.cname for c in components},
                  inplace=True)
    return result

#%%

def growth_vars(data, columns=[], date_var=None, by=None,
                periods=1, baseline=None, method="relpct"):
    """
    Calculate growth for columns in a dataframe

    Parameters
    ----------
    data: DataFrame
        Dataframe including a date column and one or more columns for which
        to calculate growth.

    columns: str | GrowthComponent | list[str | GrowthComponent]
        Names of columns for which to calculate growth.

    date_var: str, optional
        Name of column whose values determine temporal order among data rows.

    by: str, optional
        Name of column used to determine groups for `groupby`.

    periods: int, default 1
        Lag, in number of rows, for calculating growth within time series.
        Ignored if `baseline` is specified.

    baseline: "first", numeric, Series or DataFrame
        Value or values to calculate growth relative to.  If "first",
        cumulative growth is calculated relative to the row with the smallest
        value of `date_var`.  If `baseline` is not given, growth is
        calculated within each time series.  If a DataFrame, revisions are
        calculated comparing `data` to `baseline`; columns of `baseline`
        should include `columns`, and may or may not include `by`.
    method: str, default "relpct"
        Comparison method, passed to `dutils.compare()`.

    Returns
    -------
    DataFrame with same index as `data`, and columns from `columns`.

    Examples
    --------
    # Period-on-period
    growth_vars(df, columns=["gva"], date_var="date", periods=1)

    # Cumulative growth
    growth_vars(df, columns=["gva"], date_var="date", baseline="first")

    # Growth relative to single date.
    growth_vars(df, columns=["gva"], date_var="date", baseline={"date": "2019 Q4"})

    # Revisions from comparable dataframe.
    growth_vars(df, columns=["gva"], baseline=df_baseline)


    # Growth relative to single date, with a split factor.
    growth_vars(df, columns=["gva"], date_var="date", by="industry", baseline={"date": "2019 Q4"})

    # Same as:
    baseline = data.loc[df["date"]=="2019 Q4", :].groupby("industry")["gva"].first()
    growth_vars(df, columns=["gva"], date_var="date", baseline=baseline)


    # Relative to calculated baseline for each level of `by`
    baseline = data.loc[data["year"]=="2019", :].groupby("industry")["gva"].mean()
    growth_vars(df, columns=["gva"], by="industry", baseline=baseline)
    """

    """
    Essential functionality:

    Period-on-period growth and component contributions to it
        - Baseline is value of each variable at lag 1 within each by group
          (sorted by date_var within by groups)
    Cumulative growth and component contributions to it
        - Baseline is value of each variable at earliest time point within
          each by group
    Revision percent and component contributions to it
        - Baseline is value of each variable in dataframe of similar shape,
          with mostly compatible date_var and by variable.
    """

    # Ensure data columns include the ones we need.
    if date_var is not None:
        assert date_var in data.columns
    if by is not None:
        assert by in data.columns

    if isinstance(columns, (str, GrowthComponent)):
        # Put single column item into a list, for downstream consistency.
        columns = [columns]

    column_names = [getattr(col, "name", col) for col in columns]
    assert all(col in data.columns for col in column_names), \
        f"Some of {column_names} are missing from data columns {data.columns}"

    if baseline is None:
        # Period-on-period growth.
        if date_var is not None:
            data = data.sort_values(date_var, kind="stable", ignore_index=True)

        if by is None:
            df_baseline = data.shift(periods=periods)
        else:
            df_baseline = data.groupby(by, sort=False).shift(periods=periods)

        # if date_var is not None:
        #     # Sort the data (ideally would sort by date but not by `by`).
        #     sort_keys = date_var if by is None else [by, date_var]
        #     data = data.sort_values(sort_keys)

        # if by is not None:
        #     # Group the data.
        #     df_baseline = data.groupby(by, sort=False).shift(periods=periods)
        # else:
        #     df_baseline = data.sort_values(date_var).shift(periods=periods)

        result = _df_weighted_diff(data, df_baseline,
                                   columns=columns,
                                   method=method)
    elif isinstance(baseline, pd.DataFrame):
        # Revision percent.
        id_vars = [var for var in [by, date_var] if var is not None]
        if id_vars != []:
            data = data.set_index(id_vars)
            baseline = baseline.set_index(id_vars)
        result = _df_weighted_diff(data, baseline,
                                   columns=columns,
                                   method=method)
        if id_vars != []:
            result.reset_index(inplace=True)
    elif isinstance(baseline, str):
            # Cumulative growth relative to first value in each split group.
            assert(baseline == "first")
            if by is None:
                baseline = data[column_names].apply(
                    lambda c: c.loc[c.first_valid_index()])
                df_baseline = data.assign(**baseline.to_dict())
            else:
                baseline = data.groupby(by)[column_names].first()
                df_baseline = (
                    data.drop(columns=column_names)
                    .join(baseline, on=by))
            result = _df_weighted_diff(
                data,
                df_baseline,
                columns=columns,
                method=method)
    else:
        # Growth relative to column values - require dict, or series to find data.
        if isinstance(baseline, dict):
            baseline = pd.Series(baseline)

        assert isinstance(baseline, pd.Series), \
               f"Expected dict, or Series, not {type(baseline)}"
        baseline_df_alignment = data.align(baseline,
                                           axis=1,
                                           join="inner",
                                           copy=False)
        baseline_eq = pd.DataFrame.eq(*baseline_df_alignment)
        if by is not None:
            baseline_values_by_split = data[baseline_eq.all(1)] \
                .groupby(by).mean(numeric_only=True)
            df_baseline = data.drop(columns=baseline_values_by_split.columns) \
                .join(baseline_values_by_split, on=by)
        else:
            raise NotImplementedError(
                "Cumulative growth without `by` is not implemented")
        result = _df_weighted_diff(data, df_baseline,
                                   columns=columns,
                                   method=method)
    return result


#%%
if False:
    # Some unit tests for early debug.

    df = pd.DataFrame.from_records([
        ["2020", "A", 100, .25],
        ["2021", "A", 110, .75],
        ["2020", "B", 100, .75],
        ["2021", "B", 105, .25],
        ], columns=["date", "industry", "gva", "cpshare"])
    column_names = ["gva"]

    ## Period-on-period growth - require lag.
    result = growth_vars(df, columns=["gva"], date_var="date", by="industry")
    result = growth_vars(df, columns=[GrowthComponent("gva", -1, "-gva")],
                         date_var="date", by="industry")
    result = growth_vars(df,
                         columns=[SignReversedComponent("gva")],
                         date_var="date", by="industry")
    result = growth_vars(df,
                         columns=[GrowthComponent("gva", "cpshare",
                                                  "weighted gva")],
                         date_var="date", by="industry")


    ## Cumulative growth - require "first", dict, or series to find data.
    result = growth_vars(df, columns=["gva"], date_var="date", by="industry",
                         baseline="first")
    result = growth_vars(df, columns=["gva"], date_var="date", by="industry",
                         baseline={"date": "2021"})
    result = growth_vars(df, date_var="date", by="industry",
                         columns=[GrowthComponent("gva", "cpshare",
                                                  "weighted gva")],
                         baseline="first")


    ## Revision percent - require Dataframe for comparison.
    df_other = df.assign(gva=df["gva"]*0.5,
                         cpshare=1-df["cpshare"])
    result = growth_vars(df, date_var="date", by="industry",
                         columns=[GrowthComponent("gva", "cpshare",
                                                  "weighted gva")],
                         baseline=df_other)
