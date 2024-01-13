from bccov import config
from bccov.utils.commands import run_cmd


def build_runtime():
    run_cmd("make", cwd=config.RUNTIME_DIR, verbose=True)


def link_runtime(input_bitcode: str, output_bitcode: str):
    run_cmd(
        f"{config.LLVM_LINK} {input_bitcode} {config.RUNTIME_DIR}/runtime.bc -o {output_bitcode}",
        verbose=True,
    )
