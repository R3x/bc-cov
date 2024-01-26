import argparse
import os
import pathlib

from bccov.compile import build_binary
from bccov.config import TESTS_DIR, set_config
from bccov.coverage import (
    highlight_lines,
    parse_cov_info_file,
    parse_coverage_file,
    print_coverage_stats,
)
from bccov.indexer import create_code_database, get_function_source
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
    parser.add_argument(
        "-f",
        "--function",
        help="Name of the function to get source of",
        type=str,
        default="",
    )
    parser.add_argument(
        "--skip-file",
        help="File containing list of functions to skip",
        type=pathlib.Path,
        default=pathlib.Path(TESTS_DIR / "griller.skip"),
    )
    parser.add_argument(
        "--tracepc",
        help="Enable ordered tracing of basic blocks",
        action="store_true",
    )
    parser.add_argument(
        "--bbcov",
        help="Enable profiling-style, thread-safe basic block coverage",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.tracepc and not args.bbcov:
        print("No instrumentation selected. Exiting.")
        exit(1)

    if args.tracepc and args.bbcov:
        print("Only one instrumentation can be selected. Exiting.")
        exit(1)

    set_config(args.config_file)
    if args.debug:
        set_global_log_level("DEBUG")
    build_passes()
    build_runtime()

    if args.tracepc:
        tracepc(args)
    elif args.bbcov:
        bbcov(args)


def tracepc(args: argparse.Namespace):
    run_passes(
        pass_name="CovInstrument",
        bitcode_file=args.bitcode_file,
        output_bitcode_file="/tmp/instrumented.bc",
        output_cov_info_file="/tmp/cov_info.json",
        skip_file=args.skip_file,
    )
    link_runtime(
        pathlib.Path("/tmp/instrumented.bc"),
        pathlib.Path("/tmp/final_linked.bc"),
        args.debug,
    )


def bbcov(args: argparse.Namespace):
    run_passes(
        pass_name="CovInstrument",
        bitcode_file=args.bitcode_file,
        output_bitcode_file="/tmp/instrumented.bc",
        output_cov_info_file="/tmp/cov_info.json",
        skip_file=args.skip_file,
    )
    link_runtime(
        pathlib.Path("/tmp/instrumented.bc"),
        pathlib.Path("/tmp/final_linked.bc"),
        args.debug,
    )
    build_binary("/tmp/final_linked.bc", "/tmp/final_binary")
    parse_cov_info_file(pathlib.Path("/tmp/cov_info.json"))
    create_code_database(args.source_dir)

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
    sources = get_function_source(args.function)
    highlight_lines(args.function, sources)
