"""
Save CSV with labour productivity data by industry

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, `ukons_lprod_to_csv` reads an Excel file
containing UK Office for National Statistics (ONS) labour productivity data,
and creates a `.csv` file with either annual or quarterly time series of
productivity, gross value added, and labour index values.

Command line interface
----------------------
usage: ukons_lprod_to_csv.py [-h] (-A | -Q) [-b | -o] [-S | -D | -B] [-g ARGS]
                             [-t SAVE]
                             datafile

Get corresponding labour productivity, gross value added and labour data

positional arguments:
  datafile              File (.xls) formatted like ONS 'Output per hour'
                        dataset

optional arguments:
  -h, --help            show this help message and exit
  -A, --annual          Annual series
  -Q, --quarterly       Quarterly series
  -b, --balanced        Balanced GVA (whole economy only)
  -o, --output          Output approach (low level aggregates) (default)
  -S, --section         By SIC industry section (default)
  -D, --division        By SIC industry division
  -B, --bespoke         Bespoke industry aggregations
  -g ARGS, --args ARGS  Keyword arguments(?)
  -t SAVE, --save SAVE  Save file (.csv), if different from the datafile base


Application program interface (API)
-----------------------------------
GVA_TABLE_MAP
    Mapping of mappings to worksheet names.  The main keys are "annual" and
    "quarterly".  The value for each is a mapping from keys "balanced",
    "bespoke", "section" or "division" to a worksheet name for the
    corresponding gross value added (GVA) chain volume index (CVM) data.

read_lprod
    Read ONS labour productivity data.
"""

import argparse
import re
import yaml

from collections import defaultdict
from pathlib import Path

from xplorts.dutils import find_in_metadata, read_sheet

#%%

# Map granularity to names of GVA worksheets in OpH dataset.
_OPH_GVA_TABLE_MAP = {
    "annual": {
        "balanced": "Table_1",
        "bespoke": "Table_7",
        "section": "Table_14",
        "division": "Table_21"
    },
    "quarterly": {
        "balanced": "Table_28",
        "bespoke": "Table_34",
        "section": "Table_42",
        "division": "Table_50"
    }
}

# Map granularity to names of GVA worksheets in OpJ dataset.
_OPJ_GVA_TABLE_MAP = {
    "annual": {
        "balanced": "Table_1",
        "bespoke": "Table_7",
        "section": "Table_14",
        "division": "Table_21"
    },
    "quarterly": {
        "balanced": "Table_28",
        "bespoke": "Table_34",
        "section": "Table_42",
        # No quarterly division tables
    }
}

# Map granularity to names of GVA worksheets in OpW dataset.
_OPW_GVA_TABLE_MAP = {
    "annual": {
        "balanced": "Table_1",
        "bespoke": "Table_7",
        # No annual section tables
        # No annual division tables
    },
    "quarterly": {
        "balanced": "Table_13",
        "bespoke": "Table_19",
        # No annual section tables
        # No annual division tables
    }
}

#%%

def parse_lprod(data, name=None):
    """
    Parse ONS labour productivity data

    Parse a dataframe containing raw content of a worksheet from
    an Excel file like "Output per hour worked",
    "Output per job" or "Output per worker".

    Parameters
    ----------
    data : dataframe
        Worksheet containing data of interest, as strings.
    name : str
        Name to assign to the returned frame.  Typically reflects the
        content of the table, e.g. "gva", "hours", etc.  If not given,
        a name is derived from metadata in the top left corner of the
        worksheet.

    Returns
    -------
    Dataframe in wide format, with `frame.index.name` set to "date",
    `frame.columns.name set to "industry", and `frame.name` set to
    `name`.
    """

    ID_VAR = "date"
    VAR_NAME = "industry"

    if name is None:
        # Identify content from cell A1 metadata.
        metadata = data.iloc[0, 0].lower()

        # Map substrings to measure names.
        METADATA_MAP = {
            "output per hour": "oph",
            "output per job": "opj",
            "output per worker": "opw",
            "gross value added": "gva",
            "hours worked": "hours",
            "jobs": "jobs",
            "workers": "workers",
            }
        substring = find_in_metadata(METADATA_MAP, metadata)
        name = None if substring is None else METADATA_MAP[substring]

    # Find "SIC 2007" in column A.
    has_sic2007 = data[0].str.startswith("SIC 2007")
    headers = data.loc[has_sic2007, :].set_index(0).T
    headers.columns = ["section", "division"]

    # Join headers into single string for each column.
    headers = headers.section + ": " + headers.division
    headers = headers.str.replace("A to T: 01 to 98", "WE") \
        .str.replace("Part of (.*): ", r"\1.")  # "Part of C: blah" => "C.blah"

    last_header_row = data.index[has_sic2007].values[-1]
    df = data.iloc[last_header_row + 2:, :]
    df.columns = [ID_VAR, *headers]
    df.set_index(ID_VAR, inplace=True)
    df.columns.name = VAR_NAME
    df.name = name
    return df

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
        description="Get corresponding labour productivity, gross value added and labour data"
    )
    parser.add_argument("datafile",
                        help="File (.xls) formatted like ONS 'Output per hour' dataset")

    period_group = parser.add_mutually_exclusive_group(required=True)
    period_group.add_argument("-A", "--annual", action="store_true",
                        help="Annual series")
    period_group.add_argument("-Q", "--quarterly", action="store_true",
                        help="Quarterly series")


    gdp_group = parser.add_mutually_exclusive_group(required=False)
    gdp_group.add_argument("-b", "--balanced", action="store_true",
                           help="Balanced GVA (whole economy only)")
    gdp_group.add_argument("-o", "--output", action="store_true",
                           help="Output approach (low level aggregates) (default)")


    granularity_group = parser.add_mutually_exclusive_group(required=False)
    granularity_group.add_argument("-S", "--section", action="store_true",
                        help="By SIC industry section (default)")
    granularity_group.add_argument("-D", "--division", action="store_true",
                        help="By SIC industry division")
    granularity_group.add_argument("-B", "--bespoke", action="store_true",
                        help="Bespoke industry aggregations")

    parser.add_argument("-g", "--args",
                        type=str,
                        help="Keyword arguments(?)")

    parser.add_argument("-t", "--save", type=str,
                        help="Save file (.csv), if different from the datafile base")

    args = parser.parse_args()

    # Unpack YAML args into dict of dict of keyword args for various figures.
    # Will return an empty dict if no --args option specified.
    args.args = {} if args.args is None else yaml.safe_load(args.args)
    args.args = defaultdict(dict, args.args)

    return(args)

#%%

# Make class that supports adding increment to a table name.
class _TableName():
    def __init__(self, name):
        self.name = name

    def __add__(self, inc):
        return re.sub(r"_(.*)$", lambda match: f"_{int(match.group(1)) + inc}", self.name)

#%%

if __name__ == "__main__":
    # Running from command line.

    args = _parse_args()
    print(args)

    filepath = Path(args.datafile)

    period = "annual" if args.annual else "quarterly"
    gdp_type = "balanced" if args.balanced else "output"
    granularity = "bespoke" if args.bespoke else (
        "division" if args.division else "section"
    )

    # Determine whether dataset is oph, opj, or opw.
    df_annual_bespoke_lprod = read_sheet(
        args.datafile,
        sheet_name="Table_11",
        sheet_parser=parse_lprod)
    dataset = df_annual_bespoke_lprod.name

    # Get mapping from granularity to the dataset's GVA worksheet.
    gva_table_map = {
        "oph": _OPH_GVA_TABLE_MAP,
        "opj": _OPJ_GVA_TABLE_MAP,
        "opw": _OPW_GVA_TABLE_MAP
        }[dataset]

    # Identify which set of annual or quarterly data is specified.
    gva_key2 = "balanced" if args.balanced else granularity

    # Make mapping from gva, labour and lprod to worksheets.
    worksheets = {"gva": gva_table_map[period][gva_key2]}
    worksheets["labour"] = _TableName(worksheets["gva"]) + 2
    worksheets["lprod"] = _TableName(worksheets["gva"]) + 4

    df_map = {measure: read_sheet(args.datafile,
                                  sheet_name=worksheet,
                                  sheet_parser=parse_lprod)
              for measure, worksheet in worksheets.items()}
    # df_map = {measure: read_lprod(args.datafile, worksheets[measure], value_name=measure)
    #           for measure in ("lprod", "gva", "labour")}

    lprod_long = df_map["lprod"].join([df_map[key] for key in ("gva", "labour")])         .reset_index()
    print(lprod_long.head())

    outfile = args.save if args.save is not None else filepath.with_suffix(".csv")
    lprod_long.to_csv(outfile, index=False)
