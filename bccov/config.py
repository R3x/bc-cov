import json
import pathlib

LLVM_OPT = "opt"


def set_config(path_to_config: pathlib.Path):
    global LLVM_OPT

    assert path_to_config.exists(), f"Config file {path_to_config} does not exist"

    try:
        with open(path_to_config, "r") as f:
            config = json.load(f)
            LLVM_OPT = config.get("LLVM_OPT", LLVM_OPT)

    except json.decoder.JSONDecodeError as e:
        raise Exception(f"Config file {path_to_config} is not a valid JSON file") from e
