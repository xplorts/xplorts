"""
Make a standalone app showing interactive revision heatmaps

When run from the command line, reads data from a CSV file and
creates an HTML document that displays three heatmap tabs showing
the size of revisions in a time series dataset compared to an
earlier vintage of the same series.  There are tabs for revisions
to levels, revisions to growth rates, and revisions to cumulative
growth.

In the CSV file, the first row of data defines column names.
The file should include:
    - a column of dates (annual, quarterly or monthly),
    - a column of category names, and
    - columns of data values (levels or indexes).

An interactive bokeh app is created, displaying three tabs.
Each tab shows a pair of heatmaps for revision percentages and
absolute revision percentages, with dates along the horizontal
axis, category names along the vertical axis, and a selector
widget to switch from one data measure to another.

The interactive app is saved as an HTML file which requires
a web browser to view, but does not need an active internet connection.
Once created, the HTML file does not require Python,
so it is easy to share the interactive app.

Command line interface
----------------------
usage: xp-diff [-h] [-l LEVELS [LEVELS ...]]
                    [-i INDEXES [INDEXES ...]] [-b BY] [-d DATE]
                    [-t SAVE] [-s]
                    from-file to-file

Make a standalone app showing interactive revision heatmaps in a web browser

positional arguments:
  from-file             File (CSV) with original data series and split factor
  to-file               File (CSV) with newer data

optional arguments:
  -h, --help            show this help message and exit
  -l LEVELS [LEVELS ...], --levels LEVELS [LEVELS ...]
                        Variables of levels data
  -i INDEXES [INDEXES ...], --indexes INDEXES [INDEXES ...]
                        Variables of index data (will show growth revisions
                        only)
  -b BY, --by BY        Factor variable for splits
  -d DATE, --date DATE  Date variable
  -t SAVE, --save SAVE  Interactive .html to save, if different from the
                        datafile base
  -s, --show            Show interactive .html

"""

#%%

from bokeh.io import save, show
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource, Div, Tabs

import argparse
from pathlib import Path
import pandas as pd
import sys

from xplorts.base import filter_widget, set_output_file, unpack_data_varnames
from xplorts.diff import RevisedTS, revtab

#%%

def difftabs(data):
    """
    Return Bokeh Tabs object with three revision tabs

    Parameters
    ----------
    data : RevisedTS
        Time series dataset with two vintages.

    Returns
    -------
    Tabs
        Includes a tab for level revisions, growth revisions, and revisions
        in cumulative growth.
    """
    # Widget for selecting which measure to show.
    widget = (filter_widget(data.all_measures, title="Measure")
              if len(data.all_measures) > 1
              else None)

    cds_diff_levels = ColumnDataSource(
        data.revisions()
    )

    cds_diff_growth = ColumnDataSource(
        data
            .calc_growth()
            .revisions(method="diff")
    )

    cds_diff_cumgrowth = ColumnDataSource(
        data
            .calc_growth(baseline="first")
            .revisions(method="diff")
    )

    tabs = [
        revtab(revdata, title=revtitle,
               x=data.date, y=data.by,
               values=(widget if widget is not None else data.all_measures[0]),
               )
        for revdata, revtitle in [
                (cds_diff_levels, "Level revisions"),
                (cds_diff_growth, "Growth revisions"),
                (cds_diff_cumgrowth, "Revisions of cumulative growth")
                ]
        ]

    return Tabs(tabs=tabs)

#%%

def _parse_args():
    """
    Parse command line arguments

    Returns
    -------
    `argparse.Namespace` object

    Examples
    --------
    args = _parse_args()
    data = pd.read_csv(args.datafile)

    Resources
    ---------
    [argparse — Parser for command-line options, arguments and sub-commands](https://docs.python.org/3/library/argparse.html#dest)
    """
    # Check command line arguments.
    parser = argparse.ArgumentParser(
        prog="python -m xplorts.diff",
        description="Make a standalone app showing interactive revision heatmaps in a web browser"
    )
    parser.add_argument("from-file",
                        help="File (CSV) with original data series and split factor")

    parser.add_argument("to-file",
                        help="File (CSV) with newer data")

    parser.add_argument("-l", "--levels",
                        nargs="+", type=str,
                        help="Variables of levels data")

    parser.add_argument("-i", "--indexes",
                        nargs="+", type=str,
                        help="Variables of index data (will show growth revisions only)")

    parser.add_argument("-b", "--by", type=str,
                        help="Factor variable for splits")

    parser.add_argument("-d", "--date", type=str,
                        help="Date variable")

    parser.add_argument("-t", "--save", type=str,
                        help="Interactive .html to save, if different from the datafile base")

    parser.add_argument("-s", "--show", action="store_true",
                        help="Show interactive .html")

    args = parser.parse_args()
    return(args)


#%%
def main():
    """Entry point for diff command line"""

    args = _parse_args()

    from_file = getattr(args, "from-file")
    to_file = getattr(args, "to-file")

    data_old = pd.read_csv(from_file, dtype=str)
    data_new = pd.read_csv(to_file, dtype=str)

    print(data_new.head())

    title = "diff: " + Path(to_file).stem

    # Configure output file for interactive html.
    set_output_file(
        args.save or to_file,
        title = title
    )

    # Unpack args specifying which data columns to use.
    varnames = unpack_data_varnames(
        args,
        ["date", "by", "levels", "indexes"],
        data_new.columns)

    data_rts = RevisedTS(data_new, original=data_old,
                         **varnames)

    # Convert str to float so we can plot the data.
    dependent_variables = data_rts.all_measures
    for vintage in data_rts:
        df = data_rts[vintage]
        df[dependent_variables] = df[dependent_variables].astype(float)

    tabs = difftabs(data_rts)

    # Make app that shows tabs of various charts.
    app = layout([
        Div(text="<h1>" + "Revisions 'new' vs 'original'"),  # Show title as level 1 heading.
        tabs
        ])

    if args.show:
        show(app)  # Save file and display in web browser.
    else:
        save(app)  # Save file.

if __name__ == "__main__":
    sys.exit(main())





#%% Move to test code?
if False:
    data_original = pd.DataFrame.from_records(
        [("2010 Q1", "A", 100),
         ("2010 Q2", "A", 102),
         ("2010 Q3", "A", 104),

         ("2010 Q1", "B", 100),
         ("2010 Q2", "B", 104),
         ("2010 Q3", "B", 108)],
        columns=["date", "industry", "gva"]
        )
    data_original["date"] = data_original["date"].astype(str)
    data_original["hours"] = data_original["gva"].values[::-1] * 1.1

    data_new = pd.DataFrame.from_records(
        [("2010 Q1", "B", 110),
         ("2010 Q2", "B", 130),
         ("2010 Q3", "B", 150),
         ("2010 Q4", "B", 170),

         ("2010 Q1", "A", 110),
         ("2010 Q2", "A", 120),
         ("2010 Q3", "A", 130),
         ("2010 Q4", "A", 140)],
        columns=["date", "industry", "gva"]
        )
    data_new["date"] = data_new["date"].astype(str)
    data_new["hours"] = data_new["gva"].values[::-1] * 0.9

    data_rts = RevisedTS(data_new, original=data_original,
                         date="date", by="industry", indexes=["gva", "hours"])

    g = data_rts.calc_growth(periods=1)
    g.data

    tabs = difftabs(data_rts)

    # Make app that shows tabs of various charts.
    app = layout([
        Div(text="<h1>" + "Revisions 'new' vs 'original'"),  # Show title as level 1 heading.
        tabs
        ])
    show(app)
