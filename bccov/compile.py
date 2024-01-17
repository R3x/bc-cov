import os

from bccov import config
from bccov.utils.commands import run_cmd


def build_binary(bitcode_file: str, output_file: str):
    cflags = os.environ.get("CFLAGS", "")
    run_cmd(f"clang {cflags} -g {bitcode_file} -o {output_file}", verbose=True)
