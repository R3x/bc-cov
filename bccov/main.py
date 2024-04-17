import argparse
import os
import pathlib
import uuid

from bccov.compile import build_binary
from bccov.config import TESTS_DIR, set_config
from bccov.coverage import (
    enable_comparison_mode,
    highlight_lines,
    parse_cov_info_file,
    parse_coverage_file,
    print_coverage_stats,
    print_coverage_summary,
    print_files_covered_by_line,
)
from bccov.indexer import create_code_database, get_function_source
from bccov.llvm import build_passes, run_passes
from bccov.runtime import build_runtime, link_runtime, run_and_collect_coverage
from bccov.utils.pylogger import get_logger, set_global_log_level

log = get_logger(__name__)


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
    parser.add_argument(
        "-ccm",
        "--compare-compilers-mode",
        help="Enable compiler comparison mode",
        action="store_true",
    )
    parser.add_argument(
        "-afl",
        help="Treat the input directory as an AFL input directory",
        action="store_true",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        help="Dump results to a output file",
        type=pathlib.Path,
    )
    parser.add_argument(
        "-ps",
        "--print-stats",
        help="Print coverage stats",
        action="store_true",
    )
    parser.add_argument(
        "--line",
        help="Dump the names of the files that reach the line",
        type=int,
    )

    args = parser.parse_args()
    if not args.tracepc and not args.bbcov:
        print("No instrumentation selected. Exiting.")
        exit(1)

    if args.tracepc and args.bbcov:
        print("Only one instrumentation can be selected. Exiting.")
        exit(1)

    if args.compare_compilers_mode:
        if args.bbcov:
            print("Comparison mode not supported for bbcov. Exiting.")
            exit(1)

    set_config(args.config_file)
    if args.debug:
        set_global_log_level("DEBUG")
    build_passes()
    build_runtime()

    if args.compare_compilers_mode:
        compare_compilers(args)
    else:
        if args.tracepc:
            tracepc(args)
        elif args.bbcov:
            bbcov(args)


def compare_compilers(args: argparse.Namespace):
    # TODO: this is incomplete ATM
    # Hardcode compilers for now
    COMPILERS = ["clang", "~/griller_utils/AFLplusplus/afl-clang-fast"]
    run_passes(
        pass_name="CovInstrument",
        bitcode_file=args.bitcode_file,
        output_bitcode_file="/tmp/instrumented.bc",
        output_cov_info_file="/tmp/cov_info.json",
        skip_file=args.skip_file,
        flags="-tracepc",
    )
    link_runtime(
        pathlib.Path("/tmp/instrumented.bc"),
        pathlib.Path("/tmp/final_linked.bc"),
        args.debug,
        "tracepc",
    )

    enable_comparison_mode()
    parse_cov_info_file(pathlib.Path("/tmp/cov_info.json"), mode="tracepc")
    create_code_database(args.source_dir)
    for cid, compiler in enumerate(COMPILERS):
        build_binary("/tmp/final_linked.bc", f"/tmp/bin{cid}", compiler)

    for input_file in args.input_dir.glob("*"):
        if not input_file.is_file():
            continue
        for cid, compiler in enumerate(COMPILERS):
            run_and_collect_coverage(
                pathlib.Path(f"/tmp/bin{cid}"),
                pathlib.Path("/tmp/target.bc_cov"),
                input_file,
            )
            parse_coverage_file(pathlib.Path("/tmp/target.bc_cov"), mode="tracepc")


def tracepc(args: argparse.Namespace):
    log.info("Running Instrumentation passes")
    run_passes(
        pass_name="CovInstrument",
        bitcode_file=args.bitcode_file,
        output_bitcode_file="/tmp/instrumented.bc",
        output_cov_info_file="/tmp/cov_info.json",
        skip_file=args.skip_file,
        flags="-tracepc",
    )
    log.info("Linking runtime")
    link_runtime(
        pathlib.Path("/tmp/instrumented.bc"),
        pathlib.Path("/tmp/final_linked.bc"),
        args.debug,
        "tracepc",
    )
    log.info("Compiling binary")
    build_binary("/tmp/final_linked.bc", "/tmp/final_binary")
    log.info("Parsing coverage info")
    parse_cov_info_file(pathlib.Path("/tmp/cov_info.json"), mode="tracepc")
    log.info("Creating code database")
    create_code_database(args.source_dir)

    if args.afl:
        log.info("Trying all crashes in AFL input directory")
        for input_file in args.input_dir.glob("default/crashes/*"):
            if not input_file.is_file():
                continue
            run_and_collect_coverage(
                pathlib.Path("/tmp/final_binary"),
                pathlib.Path("/tmp/target.bc_cov"),
                input_file,
            )
            parse_coverage_file(pathlib.Path("/tmp/target.bc_cov"), mode="tracepc")

        log.info("Trying all queue inputs in AFL input directory")
        for input_file in args.input_dir.glob("default/queue/*"):
            if not input_file.is_file():
                continue
            run_and_collect_coverage(
                pathlib.Path("/tmp/final_binary"),
                pathlib.Path("/tmp/target.bc_cov"),
                input_file,
            )
            parse_coverage_file(pathlib.Path("/tmp/target.bc_cov"), mode="tracepc")
    else:
        log.info("Trying all inputs in input directory")
        for input_file in args.input_dir.glob("*"):
            if not input_file.is_file():
                continue
            run_and_collect_coverage(
                pathlib.Path("/tmp/final_binary"),
                pathlib.Path("/tmp/target.bc_cov"),
                input_file,
            )
            parse_coverage_file(pathlib.Path("/tmp/target.bc_cov"), mode="tracepc")

    if args.print_stats:
        print_coverage_stats(mode="tracepc")
    print_coverage_summary("tracepc", args.function)
    sources = get_function_source(args.function)
    highlight_lines(
        args.function, sources, mode="tracepc", output_file=args.output_file
    )


def bbcov(args: argparse.Namespace):
    id = str(uuid.uuid4())[0:8]
    log.info("Running Instrumentation passes")
    run_passes(
        pass_name="CovInstrument",
        bitcode_file=args.bitcode_file,
        output_bitcode_file=f"/tmp/instrumented-{id}.bc",
        output_cov_info_file=f"/tmp/cov_info-{id}.json",
        skip_file=args.skip_file,
        flags="-bbcount",
    )

    log.info("Linking runtime")
    link_runtime(
        pathlib.Path(f"/tmp/instrumented-{id}.bc"),
        pathlib.Path(f"/tmp/final_linked-{id}.bc"),
        args.debug,
        "bbcov",
    )

    log.info("Compiling binary")
    build_binary(f"/tmp/final_linked-{id}.bc", f"/tmp/final_binary-{id}")
    log.info("Parsing coverage info")
    parse_cov_info_file(pathlib.Path(f"/tmp/cov_info-{id}.json"), mode="bbcov")
    log.info("Creating code database")
    create_code_database(args.source_dir)

    if args.afl:
        log.info("Trying all crashes in AFL input directory")
        for input_file in args.input_dir.glob("default/crashes/*"):
            if not input_file.is_file():
                continue
            run_and_collect_coverage(
                pathlib.Path(f"/tmp/final_binary-{id}"),
                pathlib.Path(f"/tmp/target-{id}.bc_cov"),
                input_file,
            )
            parse_coverage_file(
                pathlib.Path(f"/tmp/target-{id}.bc_cov"),
                mode="bbcov",
                original_input=input_file,
            )

        log.info("Trying all queue inputs in AFL input directory")
        for input_file in args.input_dir.glob("default/queue/*"):
            if not input_file.is_file():
                continue
            run_and_collect_coverage(
                pathlib.Path(f"/tmp/final_binary-{id}"),
                pathlib.Path(f"/tmp/target-{id}.bc_cov"),
                input_file,
            )
            parse_coverage_file(
                pathlib.Path(f"/tmp/target-{id}.bc_cov"),
                mode="bbcov",
                original_input=input_file,
            )
    else:
        log.info("Trying all inputs in input directory")
        for input_file in args.input_dir.glob("*"):
            if not input_file.is_file():
                continue
            run_and_collect_coverage(
                pathlib.Path(f"/tmp/final_binary-{id}"),
                pathlib.Path(f"/tmp/target-{id}.bc_cov"),
                input_file,
            )
            parse_coverage_file(
                pathlib.Path(f"/tmp/target-{id}.bc_cov"),
                mode="bbcov",
                original_input=input_file,
            )

    if args.line != 0:
        print_files_covered_by_line("bbcov", args.function, args.line)

    if args.print_stats:
        print_coverage_stats(mode="bbcov")
    print_coverage_summary("bbcov", args.function)
    sources = get_function_source(args.function)
    highlight_lines(args.function, sources, mode="bbcov", output_file=args.output_file)
