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
    cmd = f"{env_vars} {compiler} {cflags} -g {bitcode_file} -o {output_file}"
    stdout, stderr = run_cmd(cmd, verbose=True) or ("", "")
    assert os.path.exists(output_file), (
        f"Failed to create output file {output_file}\n"
        f"  command: {cmd}\n"
        f"  stdout: {stdout}\n"
        f"  stderr: {stderr}"
    )
