import pathlib

from bccov import config
from bccov.utils.commands import run_cmd


def build_runtime():
    run_cmd("make clean", cwd=config.RUNTIME_DIR, verbose=False)
    run_cmd("make all", cwd=config.RUNTIME_DIR, verbose=False)


def link_runtime(
    input_bitcode: pathlib.Path,
    output_bitcode: pathlib.Path,
    debug: bool = False,
    mode: str = "",
):
    BITCODE = {"tracepc": "tracepc_runtime.bc", "bbcov": "bbcov_runtime.bc"}

    assert all(
        p.exists() and p.is_file() for p in [input_bitcode]
    ), f"Input files do not exist"

    if debug:
        run_cmd(
            f"{config.LLVM_LINK} {input_bitcode} {config.RUNTIME_DIR}/debug{BITCODE[mode]} -o {output_bitcode}",
        )
    else:
        run_cmd(
            f"{config.LLVM_LINK} {input_bitcode} {config.RUNTIME_DIR}/{BITCODE[mode]} -o {output_bitcode}",
        )


def run_and_collect_coverage(
    input_binary: pathlib.Path, output_file: pathlib.Path, input_file: pathlib.Path
):
    # Check if the input files exist
    assert input_binary.exists() and input_binary.is_file(), f"Input binary does not exist"
    assert input_file.exists() and input_file.is_file(), f"Input file does not exist"

    run_cmd(f"BC_COV_FILE={output_file} {input_binary} < {input_file}")
