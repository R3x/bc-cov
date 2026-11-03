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

    runtime_name = f"debug{BITCODE[mode]}" if debug else BITCODE[mode]
    runtime_bc = pathlib.Path(config.RUNTIME_DIR) / runtime_name
    # The runtime bitcode is built by `make -C utils/bc-cov/runtime all`
    # (also wired into lib/build.sh). If it's missing, llvm-link fails silently
    # and the absent output only surfaces later as a cryptic clang error on
    # final_binary — so fail loudly and actionably here instead.
    assert runtime_bc.exists() and runtime_bc.is_file(), (
        f"Coverage runtime bitcode missing: {runtime_bc}. "
        f"Build it with `make -C {config.RUNTIME_DIR} all` (LLVM-16 clang)."
    )

    run_cmd(
        f"{config.LLVM_LINK} {input_bitcode} {runtime_bc} -o {output_bitcode}",
    )
    assert output_bitcode.exists() and output_bitcode.is_file(), (
        f"llvm-link did not produce {output_bitcode} "
        f"(linked {input_bitcode} + {runtime_bc}); check {config.LLVM_LINK}."
    )


def run_and_collect_coverage(
    input_binary: pathlib.Path, output_file: pathlib.Path, input_file: pathlib.Path
):
    assert all(
        p.exists() and p.is_file() for p in [input_binary, input_file]
    ), f"Input files do not exist"

    run_cmd(
        f"BC_COV_FILE={output_file} {input_binary} < {input_file}",
        cwd=config.EXEC_CWD,
    )
