import pathlib

from bccov import config
from bccov.utils.commands import run_cmd


def build_runtime():
    run_cmd("make clean", cwd=config.RUNTIME_DIR, verbose=False)
    run_cmd("make all", cwd=config.RUNTIME_DIR, verbose=True)


def link_runtime(
    input_bitcode: pathlib.Path, output_bitcode: pathlib.Path, debug: bool = False
):

    assert all(
        p.exists() and p.is_file() for p in [input_bitcode, output_bitcode]
    ), f"Input files do not exist"

    if debug:
        run_cmd(
            f"{config.LLVM_LINK} {input_bitcode} {config.RUNTIME_DIR}/debugruntime.bc -o {output_bitcode}",
            verbose=True,
        )
    else:
        run_cmd(
            f"{config.LLVM_LINK} {input_bitcode} {config.RUNTIME_DIR}/runtime.bc -o {output_bitcode}",
            verbose=True,
        )


def run_and_collect_coverage(
    input_binary: pathlib.Path, output_file: pathlib.Path, input_file: pathlib.Path
):

    assert all(
        p.exists() and p.is_file() for p in [input_binary, input_file]
    ), f"Input files do not exist"

    run_cmd(f"BC_COV_FILE={output_file} {input_binary} < {input_file}")
