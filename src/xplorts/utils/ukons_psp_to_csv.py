"""
Save CSV with annual total PSP by service area, with inputs and outputs series

Can be imported as a module, or run from the command line as a Python script.

When run from the command line, `ukons_psp_to_csv` reads an Excel file
containing UK Office for National Statistics (ONS) dataset
'Public service productivity estimates: total public service',
and creates a `.csv` file with annual time series of
productivity, inputs, and outputs index values.

Command line interface
----------------------
usage: ukons_psp_to_csv.py [-h] (-A | -N) [-g ARGS] [-t SAVE] datafile

Get corresponding total public service productivity, inputs and outputs

positional arguments:
  datafile              File (.xls) formatted like ONS 'Total public service' dataset

optional arguments:
  -h, --help            show this help message and exit
  -A, --adjusted        Quality adjusted
  -N, --nonadjusted     Non-quality adjusted
  -g ARGS, --args ARGS  Keyword arguments(?)
  -t SAVE, --save SAVE  Save file (.csv), if different from the datafile base

Application program interface (API)
-----------------------------------
TABLE_MAP
    Mapping of mappings to worksheet names.  The main keys are "adjusted"
    (quality adjusted) and "nonadjusted" (non quality adjusted).  The value for
    each is a sub-mapping from keys "productivity", "inputs", or "outputs" to
    a worksheet name for the corresponding data.

read_psp
    Read ONS total public service productivity data.
"""

import argparse
import yaml

from collections import defaultdict
from pathlib import Path

from xplorts.dutils import find_in_metadata, read_sheet

#%%

TABLE_MAP = {
    "adjusted": {
        "productivity": "3",
        "inputs": "7",
        "outputs": "5",
    },
    "nonadjusted": {
        "productivity": "4",
        "inputs": "7",
        "outputs": "6",
    }
}

#%%

def parse_psp(data, name=None):
    """
    Read ONS total public service productivity data

    Reads a data table from an Excel file like "totalpspreferencetables2020".

    Parameters
    ----------
    data : dataframe
        Worksheet containing data of interest, as strings.
    name : str
        Name to assign to the returned frame.  Typically reflects the
        content of the table, e.g. "alch", "ucl", etc.  If not given,
        a name is derived from metadata in the top left corner of the
        worksheet.

    Returns
    -------
    Dataframe in wide format, with `frame.index.name` set to "date",
    `frame.columns.name set to "service", and `frame.name` set to
    `name`.
    """

    ID_VAR = "date"
    VAR_NAME = "service"

    if name is None:
        # Identify content from cell A1 metadata.
        metadata = data.iloc[0, 0].lower()

        # Map substrings to measure names.
        METADATA_MAP = {
            "productivity": "psp",
            "output": "output",
            "input": "input",
            }
        substring = find_in_metadata(METADATA_MAP, metadata)
        name = None if substring is None else METADATA_MAP[substring]

    # Find "Year" in column A.
    has_year = data[0].str.startswith("Year")
    headers = data.loc[has_year, :].set_index(0).T
    headers.columns = ["service"]
    headers = headers.service
    headers = headers.str.replace(r"\[note .*\]", "", regex=True).str.strip()

    last_header_row = data.index[has_year].values[-1]
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
        description="Get corresponding total public service productivity, inputs and outputs"
    )
    parser.add_argument("datafile",
                        help="File (.xls) formatted like ONS 'Total public service' dataset")

    adjustment_group = parser.add_mutually_exclusive_group(required=True)
    adjustment_group.add_argument("-A", "--adjusted", action="store_true",
                        help="Quality adjusted")
    adjustment_group.add_argument("-N", "--nonadjusted", action="store_true",
                        help="Non-quality adjusted")

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

if __name__ == "__main__":
    # Running from command line.

    args = _parse_args()
    print(args)

    filepath = Path(args.datafile)

    adjustment = "adjusted" if args.adjusted else "nonadjusted"
    worksheets = TABLE_MAP[adjustment]

    df_map = {measure: read_sheet(args.datafile,
                                  sheet_name=worksheets[measure],
                                  sheet_parser=parse_psp)
              for measure in worksheets}

    data = df_map["productivity"].join([df_map[key]
                                            for key in ("inputs", "outputs")]) \
        .reset_index()
    print(data.head())

    outfile = args.save if args.save is not None else filepath.with_suffix(".csv")
    data.to_csv(outfile, index=False)
