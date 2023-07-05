"""
dutils
---------
Miscellaneous data manipulation helpers

Functions
---------
accumulate_list
    Initial subsequences of increasing length from list of items.

cumulative_growth
    Percentage growth of dataframe columns relative to earliest date.

date_tuples
    Coerce monthly, quarterly, or annual dates to tuples.

dict_fill
    Map keys to values, recycling values as necessary.

growth_pct_from
    Percentage growth for a series relative to a baseline value.

growth_vars
    Calculate growth for columns in a dataframe.

index_to
    Scale data by constant so a baseline value maps to a target value.

pairwise
    Stand-in for future `itertools.pairwise()` if `itertools` is old.
"""

#%%

from itertools import cycle, tee

import numpy as np
import pandas as pd
import re

try:
    from itertools import pairwise
except ImportError:
    # Define local pairwise(), since itertools is too old to have it.
    #
    # Function is derived from
    #   https://docs.python.org/3/library/itertools.html#itertools.pairwise
    # "Copyright © 2001-2023 Python Software Foundation; All Rights Reserved"
    # Used here under the ZERO-CLAUSE BSD LICENSE FOR CODE IN THE PYTHON 3.11.3 DOCUMENTATION
    #   https://docs.python.org/3/license.html#bsd0
    def pairwise(iterable):
        """
        Stand-in for itertools.pairwise()

        pairwise('ABCDEFG') --> AB BC CD DE EF FG.
        """

        a, b = tee(iterable)
        next(b, None)  # Remove first item of second sequence.
        return zip(a, b)  # Pairs until second sequence is exhausted.


#%%

def accumulate_list(items):
    """
    Initial subsequences of increasing length from list of items

    Generator of lists.

    Examples
    --------
    gen = accumulate_list([1, 2])
    list(gen)
    # [[], [1], [1, 2]]
    """
    for i in range(len(items) + 1):
        yield items[:i]


def cumulative_growth(data, columns, date_var="date"):
    """
    Growth of specified dataframe columns relative to earliest date

    The row containing the minimum value of `date_var` provides baseline
    values for calculating growth of the columns named by `columns`.

    Parameters
    ----------
    data: DataFrame
        Dataframe including a date column and one or more columns for which
        to calculate growth.

    columns: str or list
        Names of columns for which to calculate growth.

    date_var: str, default "date"
        Name of column whose minimum value determines the baseline row of data.

    Returns
    -------
    DataFrame with same index as `data`, and columns from `columns`.
    """
    # Wrap single column name in a list, for convenience.
    columns = [columns] if isinstance(columns, str) else columns

    # Classify each row as having the earliest date or not.
    is_min_date = data[date_var] == data[date_var].min()

    # Calculate baseline for each column from row with earliest date.
    baseline = data.loc[is_min_date, columns] \
        .reindex(index=data.index, method="nearest")  # Broadcast baseline to match shape of data.
    return growth_pct_from(data[columns],
                           baseline)


def date_tuples(dates, length_threshold = np.inf):
    """
    Coerce monthly, quarterly, or annual dates to tuples

    Tuples (if converted to a list) are suitable for `bokeh` categorical axis

    Parameters
    dates : Sequence of str
        Dates which may be annual ('2021'), quarterly ('2021 Q3'), or
        monthly ('March 2021' or anything recognised by Pandas
        `.to_period()`).
    length_threshold : integer, default np.inf
        If the number of unique `dates` exceeds this threshold, only the
        last two digits of years are used.  The default is to always
        use four-digit years.  If 0 is given, only the last two digits
        of years will be used, regardless of how many different `dates`
        there are.
    """

    dates = pd.Series(dates)

    sample_date = dates[0]
    n_dates = len(dates.unique())

    if re.fullmatch("\d{4}", sample_date):
        # Annual like '2019', use as is.
        if n_dates > length_threshold:
            # Keep only last two digits of year.
            tdate = [year[-2:] for year in dates]
        else:
            tdate = list(dates)
        return tdate

    if re.fullmatch("\d{4} ?Q\d", sample_date.upper()):
        # Quarterly like '2019Q3' or '2019 Q3'.
        # Wrap in a tuple for Bokeh categorical axis.
        tdate = dates.str.split(" ").apply(tuple)
    else:
        # Maybe monthly will work.
        # Create canonical (year, Mmm) category via datetime.
        dt_dates = pd.to_datetime(dates).dt.to_period("M")
        tdate = list(zip(dt_dates.dt.year.astype(str), dt_dates.dt.month.apply('M{:02d}'.format)))

    if n_dates > length_threshold:
        # Keep only last two digits of year.
        tdate = [(year[-2:], _) for (year, _) in tdate]
    return tdate


def dict_fill(keys, values):
    """
    Map keys to values, recycling values as necessary
    """

    return dict(zip(keys, cycle(values)))


def growth_pct_from(data, baseline):
    """
    Percentage growth relative to baseline value

    Parameters
    ----------
    data: numeric, Series or DataFrame
        Data for which to calculate growth

    baseline: numeric, Series or DataFrame
        Value or values to calculate growth relative to.

    Returns
    -------
    Same shape as `data`, calculated as `(data / baseline - 1) * 100`, which
    is often written as `100 * (data - baseline)/baseline`.

    Examples
    --------
    ## Single value
    growth_pct_from(110, 100)
    # 10

    ## Year on year growth
    df = pd.DataFrame(dict(year=[2000, 2001, 2002], jobs=[40, 50, 20]))
    baseline = df.jobs[df.year == 2001].values[0]
    df["jobs_yoy"] = growth_pct_from(df, baseline)

    ## Cumulative growth for two columns
    df = pd.DataFrame(dict(
        year=[2000, 2001, 2002],
        jobs=[40, 50, 20],
        gva=[200, 250, 275]))
    baseline = df.loc[df.year == df.year.min(),
                      ("jobs", "gva")].reindex(index=df.index,
                                               method="nearest")
    df[["jobs_growth", "gva_growth"]] = growth_pct_from(df[["jobs", "gva"]],
                                                        baseline)
    df
    """

    return (data / baseline - 1) * 100


def growth_vars(data, columns=[], date_var=None, by=None,
                periods=1, baseline=None):
    """
    Calculate growth for columns in a dataframe

    Parameters
    ----------
    data: DataFrame
        Dataframe including a date column and one or more columns for which
        to calculate growth.

    columns: str or list
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
        calculated within each time series.

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
    growth_vars(df, columns=["gva"], date_var="date", baseline="2019 Q4")

    # Revisions from comparable dataframe.
    growth_vars(df, columns=["gva"], baseline=df_baseline)


    # Growth relative to single date, with a split factor.
    growth_vars(df, columns=["gva"], date_var="date", by="industry", baseline="2019 Q4")

    # Same as:
    baseline = data.loc[df["date"]==min(df["date"]), :].groupby("industry")["gva"].first()
    growth_vars(df, columns=["gva"], date_var="date", baseline=baseline)


    # Relative to calculated baseline for each level of `by`
    baseline = data.loc[data["year"]=="2019", :].groupby("industry")["gva"].mean()
    growth_vars(df, columns=["gva"], by="industry", baseline=baseline)
    """

    # Ensure data columns include the ones we need.
    if date_var is not None:
        assert date_var in data.columns
    if by is not None:
        assert by in data.columns
    assert all(col in data.columns for col in columns), \
        f"Some of {columns} are missing from data columns {data.columns}"


    # Make placeholder copy of data ready to inject results into `columns`.
    result = data.copy()
    result[columns] = np.nan

    # Expand baseline shortcuts ("first" or a value to match data[date_var]).
    if baseline == "first":
        # Put baseline at earliest date value to get cumulative growth.
        if by is not None:
            baseline = data.loc[data[date_var]==min(data[date_var]), :].groupby(by)[columns].first()
        else:
            baseline = data.loc[data[date_var]==min(data[date_var]), :]
    elif baseline is not None and not isinstance(baseline, pd.DataFrame):
        # Find column values from date_var == baseline.
        df_baseline_columns = columns + [by] if by is not None else columns
        df_baseline_raw = data.set_index(date_var).loc[baseline, df_baseline_columns]
        if by is not None:
            # Take mean for each of the columns at each level of `by`.
            baseline = df_baseline_raw.groupby(by).mean()
        else:
            # Take mean for each of the columns.
            baseline = df_baseline_raw.mean()
    elif isinstance(baseline, pd.DataFrame):
        # Expect baseline dataframe to have a value for each column, with optional `by` splits.
        pass
    else:
        assert baseline is None

    if isinstance(baseline, pd.DataFrame):
        # Get relative change of data compared to baseline dataframe.

        assert all(col in baseline.columns for col in columns), \
            f"Some of {columns} are missing from baseline columns {baseline.columns}"

        if by is not None and date_var not in baseline.columns:
            # Use `by` to look up baseline rows to find baseline values for columns.
            #  `by` dataframe should have index of `by` levels.
            baseline_values = baseline.loc[data[by], columns].values
        else:
            # Align baseline to data, and compare baseline dataframe to columns.
            join_columns = [date_var, by] if by is not None else [date_var]
            join_keys = list(pd.MultiIndex.from_frame(data[join_columns]))
            baseline_values = baseline.set_index(join_columns).loc[join_keys, columns].values

        result[columns] = growth_pct_from(data[columns],
                                          baseline=baseline_values)
    else:
        # Do period-on-period growth with each column.
        if by is not None:
            sorted_data = data.sort_values(date_var).groupby(by)[columns]
        else:
            sorted_data = data[columns].sort_values(date_var)
        result[columns] = 100 * sorted_data.pct_change(periods=periods)
    return result


def index_to(data, baseline, to=100):
    """
    Scale data so values at `baseline` map to `to`

    Examples
    --------
    # Index (2001 = 100)
    df = pd.DataFrame(dict(year=[2000, 2001, 2002], jobs=[40, 50, 20]))
    baseline = df.jobs[df.year == 2001].values[0]
    df["jobs_index"] = index_to(df.jobs, baseline)
    df
    #    year  jobs  jobs_index
    # 0  2000    40        80.0
    # 1  2001    50       100.0
    # 2  2002    20        40.0
    """

    return data / baseline * to
