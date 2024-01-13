from bccov import config
from bccov.utils.commands import run_cmd


def build_binary(bitcode_file: str, output_file: str):
    run_cmd(f"clang -g {bitcode_file} -o {output_file}", verbose=True)
