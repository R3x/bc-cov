import pathlib

from bccov import config
from bccov.utils import run_cmd


def build_passes():
    # run build.sh
    run_cmd("./build.sh", cwd=config.LIB_DIR, verbose=True)


def run_passes(
    pass_name: str,
    bitcode_file: str,
    output_bitcode_file: str,
    output_cov_info_file: str,
    skip_file: pathlib.Path,
    flags: str = "",
):
    PASS_MAP = {"CovInstrument": f"{config.LIB_DIR}/build/libCovInstrument.so"}
    # run run.sh
    skip_flag = ""
    if skip_file.exists():
        skip_flag = f"--skiplist {skip_file}"
    run_cmd(
        f"{config.LLVM_OPT} -f -load {PASS_MAP[pass_name]} -output {output_cov_info_file} {flags} {skip_flag} -cov-instrument < {bitcode_file} > {output_bitcode_file}",
        verbose=True,
    )
    output_bitcode_file = pathlib.Path(output_bitcode_file)
    assert (
        output_bitcode_file.exists() and output_bitcode_file.is_file()
    ), f"Output file {output_bitcode_file} does not exist"
