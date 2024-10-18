import argparse
import os
import pathlib
import uuid

from bccov.utils.pylogger import get_logger, set_global_log_level
from bccov.main import tracepc, bbcov

log = get_logger(__name__)

class Args(object):
    TRACEPC = 1
    BBCOV = 2
    
    def __init__(self, bitcode, input_dir, source_dir):
        self.bitcode = bitcode
        self.input_dir = input_dir
        self.source_dir = source_dir
        self.config_file = pathlib.Path(__file__).parent.parent / "config.json"
        self.debug = True
        self.skip_file = pathlib.Path(__file__).parent.parent / "griller.skip"
        
        ## defautls
        self.ccm = False
        self.afl = False
        self.output_file = None
        self.ps = False
        self.line = None

    def set_function(self, function):
        self.function = function
        
    def set_mode(self, mode):
        if mode == Args.TRACEPC:
            self.tracepc = True
            self.bbcov = False
        elif mode == Args.BBCOV:
            self.tracepc = False
            self.bbcov = True
        else:
            raise ValueError("Invalid mode")    
        
def run_tracepc_cov():
    args = Args("test.bc", "test", "test")
    args.set_function("main")
    args.set_mode(Args.TRACEPC)
    tracepc(args)
    
def run_bbcov_cov():
    args = Args("test.bc", "test", "test")
    args.set_function("main")
    args.set_mode(Args.BBCOV)
    bbcov(args)