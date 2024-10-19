import os

from bccov import config
from bccov.utils.commands import run_cmd


def build_binary(bitcode_file: str, output_file: str, compiler: str = "clang", cflags: str = ""):
    run_cmd(f"{compiler} {cflags} -g {bitcode_file} -o {output_file}", verbose=False)
