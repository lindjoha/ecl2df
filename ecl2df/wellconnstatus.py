"""Exctracts connection status history for each compdat connection that
is included in the summary data on the form CPI:WELL,I,J,K. One line is
added to the export every time a connection changes status. It is OPEN when
CPI>0 and SHUT when CPI=0. The earliest date for any connection will be OPEN,
i.e a cell can not be SHUT before it has been OPEN. This means that any cells
that are always SHUT will be excluded.

The output data set is very sparse compared to the CPI summary data.
"""

import argparse
import re
from typing import Any, List, Set, Tuple

import numpy as np
import pandas as pd
from ecl.summary import EclSum, EclSumKeyWordVector

from ecl2df import getLogger_ecl2csv

from .common import write_dframe_stdout_file


def df(unsmry_file: str) -> pd.DataFrame:
    """descr"""
    eclsum = EclSum(unsmry_file, include_restart=False, lazy_load=False)
    column_names: Set[str] = set(EclSumKeyWordVector(eclsum, add_keywords=True))
    np_dates_ms = eclsum.numpy_dates

    cpi_columns = [
        col
        for col in column_names
        if re.match("^CPI:[A-Z0-9_-]{1,8}:[0-9]+,[0-9]+,[0-9]+$", col)
    ]
    df = pd.DataFrame(columns=["DATE", "WELL", "I", "J", "K", "OP/SH"])

    for col in cpi_columns:
        colsplit = col.split(":")
        well = colsplit[1]
        i, j, k = colsplit[2].split(",")

        vector = eclsum.numpy_vector(col)

        status_changes = _get_status_changes(np_dates_ms, vector)
        for date, status in status_changes:
            df.loc[df.shape[0]] = [date, well, i, j, k, status]

    return df


def _get_status_changes(
    dates: np.ndarray, conn_values: np.ndarray
) -> List[Tuple[Any, str]]:
    """Extracts the status history of a single connection as a list of tuples
    on the form (date, status)
    """
    status_changes = []
    prev_value = 0
    for date, value in zip(dates, conn_values):
        if value > 0 and prev_value == 0:
            status_changes.append((date, "OPEN"))
        elif prev_value > 0 and value == 0:
            status_changes.append((date, "SHUT"))
        prev_value = value
    return status_changes


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser: parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        type=str,
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output csv file. Use '-' to write to stdout. "
            "Default 'well_connection_status.csv'"
        ),
        default="well_connection_status.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def wellconnstatus_main(args):
    """Entry-point for module, for command line utility"""
    logger = getLogger_ecl2csv(__name__, vars(args))
    unsmry_file = args.DATAFILE.replace(".DATA", ".UNSMRY")
    wellconnstatus_df = df(unsmry_file)
    write_dframe_stdout_file(
        wellconnstatus_df, args.output, index=False, caller_logger=logger
    )
