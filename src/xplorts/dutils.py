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

find_in_metadata
    Return first item that is a substring of metadata.

growth_pct_from
    Percentage growth for a series relative to a baseline value.

index_to
    Scale data by constant so a baseline value maps to a target value.

pairwise
    Stand-in for future `itertools.pairwise()` if `itertools` is old.

read_sheet
    Read a two-dimensional data table from an Excel file.
"""

#%%

from itertools import cycle, tee

import numpy as np
import pandas as pd
import re
import warnings

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


def find_in_metadata(items, metadata, /):
    """
    Return first item that is a substring of metadata

    Parameters
    ----------
    items : iterable
        Candidate strings that might be substrings of `metadata`.
    metadata : str
        String to search.

    Returns
    -------
    item : str, None
        First item that is a substring of `metadata`.  If no item is found,
        return None.

    Examples
    --------
    item_list = ["one", "two"]
    find_in_metadata(item_list, "Table for two")
    # "two"

    find_in_metadata(itemlist, "Two by two, one at a time")
    # "one"

    find_in_metadata(item_list, "The rain in Spain")
    # None
    """
    item = next(iter([item for item in items if item in metadata]),
               None)
    return item


def compare(data, baseline, method="relpct"):
    """
    Percentage growth relative to baseline value

    Parameters
    ----------
    data: numeric, Series or DataFrame
        Data for which to calculate growth

    baseline: numeric, Series or DataFrame
        Value or values to calculate growth relative to.

    method: "relpct", "ratio", "diff", "logpct"
        Comparison method, one of:
            "relpct"
                Relative percent, calculated as `(data / baseline - 1) * 100`
                which is often written as `100 * (data - baseline)/baseline`.
            "ratio"
                Calculated as `data / baseline`.
            "diff"
                Calculated as `data - baseline`.
            "logpct"
                Log percent, calculated as `ln(data / baseline) * 100`.
                For relative differences less than about plus or minus 5%,
                log percent values are close to simple percentage differences.
                Unlike simple percentage difference growth rates, log percent
                growth rates can be summed or averaged across time periods.

    Returns
    -------
    Same shape as `data`, calculated.

    Examples
    --------
    ## Single value
    growth_pct_from(110, 100)
    # 10

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

    if method == "relpct":
        result = (data / baseline - 1) * 100
    elif method == "logpct":
        result = np.log(data / baseline) * 100
    elif method == "ratio":
        result = data / baseline
    elif method == "diff":
        result = data - baseline
    else:
        raise ValueError(f"Expected 'relpct', 'logpct', 'ratio' or 'diff', not '{method}'")
    return result


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
    baseline = df.jobs[df.year == 2001].values[0]  # XXX Not YoY!
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

    warnings.warn(DeprecationWarning("Use compare() instead of growth_pct_from()"))
    return (data / baseline - 1) * 100


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


def read_sheet(io, sheet_name, sheet_parser,
               name=None,
               n_digits=4, **kwargs):
    """
    Read a two-dimensional data table from an Excel file

    Parameters
    ----------
    io : as for pandas `read_excel`
        Filename.
    sheet_name : str
        Worksheet to read.
    sheet_parser : callable
        Function to use for parsing a raw dataframe of worksheet content as
        strings.  Should accept one positional argument, a dataframe, and
        a keyword argument `name`.  Should return one of:
        - Dataframe in wide format, with `frame.index.name` and
          `frame.columns.name` defined.  The index should contain strings.
           Other columns should contain numbers formatted as strings.
        - Dataframe in long format with a single column named
          `value_name`, and a multi-index of two levels.  The `value_name`
          column should contain numbers formatted as strings.  The index
          levels should contain strings.
    name : str, optional
        Name to assign to data values.  Typically reflects the
        content of the table, e.g. "gva", "ulc", etc.  If not specified,
        defaults to the name attached to the parsed dataframe, or 'value'.
    n_digits : int, None
        Number of data digits to keep.  Defaults to 4, making values
        like "102.1234" or "0.1234".  If None, all digits are kept.
    kwargs : mapping
        Additional keyword arguments are passed to `read_excel`.

    Returns
    -------
    Dataframe with one
    three columns, "date", "industry"
    and `value_name`.
    """

    print(f"reading {name or 'value'} from {sheet_name}")
    df_sheet = pd.read_excel(io, sheet_name=sheet_name,
                         #engine="openpyxl",
                         header=None, dtype=str, **kwargs)

    df_data = sheet_parser(df_sheet, name=name)
    if len(df_data.index.names) == 1:
        # Reshape from wide to long format.
        value_name = df_data.name or name or "value"
        df_name = df_data.name
        df_data = df_data.melt(value_name=value_name,
                               ignore_index=False,
                               )
        df_data.name = df_name
        var_name = df_data.columns[0]
        df_data.set_index([var_name], append=True, inplace=True)

    if n_digits is not None:
        # Round off the data to reduce size a little.
        # df_data[name] = df_data[name_parsed].astype(float).round(n_digits).astype(str)
        df_data.iloc[:, 0] = df_data.iloc[:, 0].astype(float).round(n_digits).astype(str)
    return df_data
