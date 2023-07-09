"""
Save CSV with annual data from labour costs and labour income, by industry

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, reads an Excel file
containing UK Office for National Statistics (ONS) labour costs and labour
income data, and creates a `.csv` file with either annual time series of
unit labour costs, average labour costs per hour, and labour share of income.

Command line interface
----------------------
usage: python -m xplorts.utils.ukons_lcli_to_csv [-h] (-X | -L) [-g ARGS] [-t SAVE] datafile

Get corresponding labour productivity, gross value added and labour data

positional arguments:
  datafile              File (.xls) formatted like ONS 'Output per hour' dataset

optional arguments:
  -h, --help            show this help message and exit
  -X, --index           Index series
  -L, --level           Level series
  -g ARGS, --args ARGS  Keyword arguments(?)
  -t SAVE, --save SAVE  Save file (.csv), if different from the datafile base


Application program interface (API)
-----------------------------------
TABLE_MAP
    Mapping of mappings to worksheet names.  The main keys are "index" and
    "level".  The value for each is a sub-mapping from keys "ulc",
    "alch", or "lshare" to a worksheet name for the
    corresponding data.

read_lcli
    Read ONS labour costs and labour share data.
"""

import argparse
import yaml

from collections import defaultdict
from pathlib import Path

from xplorts.dutils import find_in_metadata, read_sheet

#%%

TABLE_MAP = {
    "index": {
        "ulc": "Table_1",
        "alch": "Table_3",
        "lshare": "Table_5",
    },
    "level": {
        "ulc": "Table_2",
        "alch": "Table_4",
        "lshare": "Table_6",
    }
}

#%%

def parse_lcli(data, name=None):
    """
    Parse a dataframe containing raw content of a worksheet from the
    labour costs and labour income dataset.

    Parameters
    ----------
    data : dataframe
        Worksheet containing data of interest, as strings.
    name : str
        Name to assign to the returned frame.  Typically reflects the
        content of the table, e.g. "gva", "ulc", etc.

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
        metadata = data.iloc[0, 0]

        # Map substrings to measure names.
        METADATA_MAP = {
            "unit labour cost": "ulc",
            "average labour compensation": "alch",
            "labour share": "lshare",
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
        prog="python -m xplorts.utils.ukons_lcli_to_csv",
        description="Get corresponding labour productivity, gross value added and labour data"
    )
    parser.add_argument("datafile",
                        help="File (.xls) formatted like ONS 'Output per hour' dataset")

    measure_group = parser.add_mutually_exclusive_group(required=True)
    measure_group.add_argument("-X", "--index", action="store_true",
                        help="Index series")
    measure_group.add_argument("-L", "--level", action="store_true",
                        help="Level series")

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


# Calculate new column from string dataframe.
def _calc(data, f, *, x, y, measurement="level", n_digits=4):
    result = f(data[x].astype(float),
               data[y].astype(float))
    if measurement == "index":
        result = 100 * result
    return result.round(n_digits).astype(str)

#%%

if __name__ == "__main__":
    # Running from command line.

    args = _parse_args()
    print(args)

    filepath = Path(args.datafile)

    measurement = "index" if args.index else "level"

    worksheets = {measure: TABLE_MAP[measurement][measure]
                  for measure in ["ulc", "alch", "lshare"]}

    df_map = {measure: read_sheet(args.datafile,
                                  sheet_name=worksheet,
                                  sheet_parser=parse_lcli,
                                  name=measure)
              for measure, worksheet in worksheets.items()}

    data = df_map["ulc"].join([df_map[key] for key in ("alch", "lshare")]) \
        .reset_index()

    data["oph"] = _calc(data,
                        lambda x, y: x / y,
                        x="alch", y="ulc",
                        measurement=measurement)

    data["deflator"] = _calc(data,
                        lambda x, y: x / y,
                        x="lshare", y="ulc",
                        measurement=measurement)

    print(data.head())

    outfile = args.save if args.save is not None else filepath.with_suffix(".csv")
    data.to_csv(outfile, index=False)
