import pathlib

from bccov import config
from bccov.utils import run_cmd


def build_passes():
    # run build.sh
    run_cmd("./build.sh", cwd=config.LIB_DIR, verbose=True)


def run_passes(pass_name: str, bitcode_file: str, output_file: str):
    PASS_MAP = {"CovInstrument": f"{config.LIB_DIR}/build/libCovInstrument.so"}
    # run run.sh
    run_cmd(
        f"{config.LLVM_OPT} -f -load {PASS_MAP[pass_name]} -cov-instrument < {bitcode_file} > {output_file}",
        verbose=True,
    )
    output_file = pathlib.Path(output_file)
    assert (
        output_file.exists() and output_file.is_file()
    ), f"Output file {output_file} does not exist"
