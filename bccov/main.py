import argparse
import pathlib

from bccov.config import set_config
from bccov.llvm import build_passes, run_passes
from bccov.utils.pylogger import set_global_log_level


def run_cli():
    parser = argparse.ArgumentParser(
        description="Run an LLVM pass on a bitcode file and process input and source directories."
    )
    parser.add_argument(
        "-b",
        "--bitcode_file",
        help="Path to the bitcode file",
        type=pathlib.Path,
        required=True,
    )
    parser.add_argument(
        "-i",
        "--input_dir",
        help="Path to the directory containing input files",
        type=pathlib.Path,
        required=True,
    )
    parser.add_argument(
        "-s",
        "--source_dir",
        type=pathlib.Path,
        help="Path to the directory containing source files",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--config_file",
        type=pathlib.Path,
        help="Path to the configuration file",
        default=pathlib.Path("config.json"),
    )

    args = parser.parse_args()

    set_config(args.config_file)
    set_global_log_level("DEBUG")
    build_passes()

    run_passes("CovInstrument", args.bitcode_file, "/tmp/instrumented.bc")
