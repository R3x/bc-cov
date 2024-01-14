import argparse
import pathlib

from bccov.compile import build_binary
from bccov.config import set_config
from bccov.coverage import (
    parse_cov_info_file,
    parse_coverage_file,
    print_coverage_stats,
)
from bccov.llvm import build_passes, run_passes
from bccov.runtime import build_runtime, link_runtime, run_and_collect_coverage
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
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    set_config(args.config_file)
    if args.debug:
        set_global_log_level("DEBUG")
    build_passes()
    build_runtime()

    run_passes(
        "CovInstrument", args.bitcode_file, "/tmp/instrumented.bc", "/tmp/cov_info.json"
    )
    link_runtime(
        pathlib.Path("/tmp/instrumented.bc"),
        pathlib.Path("/tmp/final_linked.bc"),
        args.debug,
    )
    build_binary("/tmp/final_linked.bc", "/tmp/final_binary")
    parse_cov_info_file(pathlib.Path("/tmp/cov_info.json"))

    for input_file in args.input_dir.glob("*"):
        if not input_file.is_file():
            continue
        run_and_collect_coverage(
            pathlib.Path("/tmp/final_binary"),
            pathlib.Path("/tmp/target.bc_cov"),
            input_file,
        )
        parse_coverage_file(pathlib.Path("/tmp/target.bc_cov"))

    print_coverage_stats()
