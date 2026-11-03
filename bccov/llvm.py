import pathlib

from bccov import config
from bccov.utils import run_cmd


def build_passes():
    # run build.sh
    run_cmd("./build.sh", cwd=config.LIB_DIR, verbose=False)


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
    # LLVM-16's opt defaults to the new pass manager and rejects the legacy
    # `-load <plugin> -cov-instrument` syntax. Load the plugin and select the
    # pass via the new-PM interface instead. The cl::opt flags below (-output,
    # --skiplist, -bbcount/-tracepc) are still parsed from opt's command line.
    run_cmd(
        f"{config.LLVM_OPT} -f -load-pass-plugin {PASS_MAP[pass_name]} -passes=cov-instrument -output {output_cov_info_file} {flags} {skip_flag} --disable-verify < {bitcode_file} > {output_bitcode_file}",
        verbose=True,
    )
    output_bitcode_file = pathlib.Path(output_bitcode_file)
    assert (
        output_bitcode_file.exists() and output_bitcode_file.is_file()
    ), f"Output file {output_bitcode_file} does not exist"
    assert (
        output_bitcode_file.stat().st_size > 0
    ), f"Output file {output_bitcode_file} is empty"
