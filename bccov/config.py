import json
import pathlib

LLVM_OPT = "opt"
LLVM_LINK = "llvm-link"

RUNTIME_DIR = None
LIB_DIR = None

CWD = None

def get_function_file_path():
    # Return the absolute path of the file containing this function
    return pathlib.Path(__file__)


TESTS_DIR = get_function_file_path().parent.parent / "tests"


def set_local_paths():
    global RUNTIME_DIR, LIB_DIR

    RUNTIME_DIR = get_function_file_path().parent.parent / "runtime"
    LIB_DIR = get_function_file_path().parent.parent / "lib"


def set_config(path_to_config: pathlib.Path):
    global LLVM_OPT, LLVM_LINK

    set_local_paths()

    if path_to_config.exists():
        try:
            with open(path_to_config, "r") as f:
                config = json.load(f)
                LLVM_OPT = config.get("LLVM_OPT", LLVM_OPT)
                LLVM_LINK = config.get("LLVM_LINK", LLVM_LINK)
        except json.decoder.JSONDecodeError as e:
            raise Exception(
                f"Config file {path_to_config} is not a valid JSON file"
            ) from e


def set_cwd(cwd: pathlib.Path):
    global CWD
    print(f"Setting CWD to {cwd}")
    CWD = cwd