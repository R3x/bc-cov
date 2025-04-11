import argparse
import os
import pathlib
import uuid

from bccov.utils.pylogger import get_logger, set_global_log_level
from bccov.main import tracepc, bbcov
from bccov.config import set_config, set_cwd
from bccov.llvm import build_passes
from bccov.runtime import build_runtime

log = get_logger(__name__)

class Args(object):
    TRACEPC = 1
    BBCOV = 2
    
    def __init__(self, bitcode, input_dir, crashes_dir, source_dir, cflags):
        self.bitcode_file = pathlib.Path(bitcode)
        self.input_dir = pathlib.Path(input_dir)
        if crashes_dir:
            self.crashes_dir = pathlib.Path(crashes_dir)
        else:
            self.crashes_dir = None
        self.source_dir = pathlib.Path(source_dir)
        self.config_file = pathlib.Path(__file__).parent.parent / "config.json"
        self.debug = True
        self.skip_file = pathlib.Path(__file__).parent.parent / "tests/griller.skip"
        self.cflags = cflags
        self.reuse_cache = False
        self.interactive = False

        assert self.bitcode_file.exists() and self.bitcode_file.is_file(), f"Bitcode file {self.bitcode_file} does not exist"
        assert self.input_dir.exists() and self.input_dir.is_dir(), f"Input directory {self.input_dir} does not exist"
        assert self.source_dir.exists() and self.source_dir.is_dir(), f"Source directory {self.source_dir} does not exist"
        
        ## defautls
        self.ccm = False
        self.afl = False
        self.output_file = None
        self.print_stats = False
        self.line = None

    def set_function(self, function):
        self.function = function
        
    def set_cwd(self, cwd):
        self.cwd = cwd
        
    def set_mode(self, mode):
        if mode == Args.TRACEPC:
            self.tracepc = True
            self.bbcov = False
        elif mode == Args.BBCOV:
            self.tracepc = False
            self.bbcov = True
        else:
            raise ValueError("Invalid mode")    

CWD=None

def setup(cwd):
    global CWD
    set_config(pathlib.Path(__file__).parent.parent / "config.json")
    set_global_log_level("INFO")
    set_cwd(cwd)
    CWD=cwd
    build_passes()
    build_runtime()

def run_tracepc_cov(bitcode_file, dirs, source_dir, target_function, cflags):
    args = Args(bitcode_file, dirs[0], dirs[1], source_dir, cflags)
    args.set_function(target_function)
    args.set_cwd(CWD)
    args.set_mode(Args.TRACEPC)
    tracepc(args)
    
def run_bbcov_cov(bitcode_file, dirs, source_dir, target_function, cflags, output_file, afl_mode=True):
    args = Args(bitcode_file, dirs[0], dirs[1], source_dir, cflags)
    args.set_function(target_function)
    args.set_cwd(CWD)
    args.set_mode(Args.BBCOV)
    args.afl = afl_mode
    args.output_file = output_file
    bbcov(args)