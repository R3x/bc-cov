import os

from bccov import config
from bccov.utils.commands import run_cmd


def build_binary(
    bitcode_file: str,
    output_file: str,
    compiler: str = "clang",
    cflags: str = "",
    env_vars: str = "",
):
    run_cmd(
        f"{env_vars} {compiler} {cflags} -g {bitcode_file} -o {output_file}",
        verbose=True,
    )
    assert os.path.exists(output_file), f"Failed to create output file {output_file}"
