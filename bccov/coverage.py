from collections import namedtuple
import json
import pathlib
import struct
import sys

from bccov.utils.pylogger import get_logger

LineDetails = namedtuple("LineDetails", ["file_name", "line_no"])
CoverageDetails = namedtuple(
    "CoverageDetails", ["coverage_index", "id", "line_details", "files"]
)
Function = namedtuple("Function", ["name", "file_name"])

log = get_logger(__name__, "INFO")


class TracePCCoverageStats:
    COV_MAP = {}
    ORDER = {}
    CMP_MAP = {}
    Counter = 0
    cmp_mode = False

    @staticmethod
    def set_cmp_mode(mode: bool):
        TracePCCoverageStats.cmp_mode = mode

    @staticmethod
    def init_cov_info(cov_info: dict):
        for bb_obj in cov_info["BasicBlock"]:
            id = bb_obj["Id"]
            linemap = []
            for line_obj in bb_obj["Coverage"]:
                linemap.append(LineDetails(line_obj["File"], line_obj["Line"]))
            TracePCCoverageStats.COV_MAP[id] = CoverageDetails(0, id, linemap, [])

    @staticmethod
    def add_cov_map(cov_map, id=None):

        for bb_id in cov_map:
            assert (
                bb_id in TracePCCoverageStats.COV_MAP
            ), f"BasicBlock {bb_id} not found in COV_MAP"

            if TracePCCoverageStats.COV_MAP[bb_id].coverage_index == 0:
                TracePCCoverageStats.COV_MAP[bb_id] = CoverageDetails(
                    1, bb_id, TracePCCoverageStats.COV_MAP[bb_id].line_details, []
                )

        if id == None:
            id = TracePCCoverageStats.Counter

        TracePCCoverageStats.Counter += 1
        TracePCCoverageStats.ORDER[id] = cov_map

    @staticmethod
    def print_stats():

        # find total unique basic block ids
        all_ids = set()
        for id, bb_ids in TracePCCoverageStats.ORDER.items():
            all_ids.update(bb_ids)

        print(f"Total unique basic blocks: {len(all_ids)}")
        print(f"Total basic blocks: {len(TracePCCoverageStats.COV_MAP)}")

    @staticmethod
    def get_lines_covered(function: str):
        covered_lines = set()
        uncovered_lines = set()

        for bb_id, bb in TracePCCoverageStats.COV_MAP.items():
            if bb.coverage_index > 0:
                for line in bb.line_details:
                    covered_lines.add(line.line_no)
            else:
                for line in bb.line_details:
                    uncovered_lines.add(line.line_no)

        intersection = covered_lines.intersection(uncovered_lines)
        return (
            covered_lines.difference(intersection),
            uncovered_lines.difference(intersection),
            intersection,
        )


class BBCovCoverageStats:
    COV_MAP = {}

    @staticmethod
    def cov_info_array_parse(cov_array: list):
        parsed_array = []
        for bb_obj in cov_array:
            id = bb_obj["Id"]
            linemap = []
            for line_obj in bb_obj["Coverage"]:
                linemap.append(LineDetails(line_obj["File"], line_obj["Line"]))
            parsed_array.append(CoverageDetails(0, id, linemap, []))
        return parsed_array

    @staticmethod
    def init_cov_info(cov_info: dict):
        BBCovCoverageStats.COV_MAP = {}
        for file_name, func_map in cov_info.items():
            for func_obj in func_map:
                f = Function(name=func_obj["Function"], file_name=file_name)
                BBCovCoverageStats.COV_MAP[f] = BBCovCoverageStats.cov_info_array_parse(
                    func_obj["BasicBlocks"]
                )

    @staticmethod
    def add_cov_map(cov_map, cov_file_name):
        for file_name, func_map in cov_map.items():
            for func_name, cov_array in func_map.items():
                f = Function(name=func_name.decode(), file_name=file_name.decode())

                assert (
                    f in BBCovCoverageStats.COV_MAP
                ), f"Function {f} not found in COV_MAP"
                assert len(cov_array) == len(
                    BBCovCoverageStats.COV_MAP[f]
                ), f"Coverage array length mismatch for {f}"

                for i in range(len(cov_array)):
                    assert (
                        i == BBCovCoverageStats.COV_MAP[f][i].id
                    ), f"Coverage index mismatch for {f} at index {i}"
                    if cov_array[i] > 0:
                        BBCovCoverageStats.COV_MAP[f][i] = CoverageDetails(
                            coverage_index=max(
                                BBCovCoverageStats.COV_MAP[f][i].coverage_index,
                                cov_array[i],
                            ),
                            id=BBCovCoverageStats.COV_MAP[f][i].id,
                            line_details=BBCovCoverageStats.COV_MAP[f][i].line_details,
                            files=BBCovCoverageStats.COV_MAP[f][i].files
                            + [cov_file_name],
                        )

    @staticmethod
    def get_function_coverage(name: str):
        for f, func in BBCovCoverageStats.COV_MAP.items():
            if f.name == name:
                return func
        return None

    @staticmethod
    def get_files_covering_line(function: str, line: int):
        files = set()
        for f, func in BBCovCoverageStats.COV_MAP.items():
            if f.name == function:
                for bb in func:
                    if bb.coverage_index > 0:
                        for line_detail in bb.line_details:
                            if line_detail.line_no == line:
                                files.update(bb.files)
        return files

    @staticmethod
    def get_lines_covered(function: str):
        # TODO: not file sensitve
        stats = BBCovCoverageStats.get_function_coverage(function)
        if stats == None:
            return (set(), set(), set())
        covered_lines = set()
        uncovered_lines = set()
        for bb in stats:
            if bb.coverage_index > 0:
                for line in bb.line_details:
                    covered_lines.add(line.line_no)
            else:
                for line in bb.line_details:
                    uncovered_lines.add(line.line_no)
        intersection = covered_lines.intersection(uncovered_lines)
        return (
            covered_lines.difference(intersection),
            uncovered_lines.difference(intersection),
            intersection,
        )

    @staticmethod
    def get_cov_map():
        return BBCovCoverageStats.COV_MAP

    @staticmethod
    def get_json_cov_map():
        SKIP_FILES = [
            "instrumentation_helpers/complex_types.c",
            "instrumentation_helpers/helper.c",
            "instrumentation_helpers/hooks.c",
            "instrumentation_helpers/list.c"
        ]
        
        # convert to json serializable format
        cov_map = {}
        for f, func in BBCovCoverageStats.COV_MAP.items():
            if f.file_name in SKIP_FILES:
                continue
            
            if f.file_name not in cov_map:
                cov_map[f.file_name] = {}
            
            cov_map[f.file_name][f.name] = []
            for bb in func:
                cov_map[f.file_name][f.name].append(
                    {
                        "Id": bb.id,
                        "CovInfo" : [
                            {"File": line.file_name, "Line": line.line_no}
                            for line in bb.line_details   
                        ],
                        "CovIndex" : bb.coverage_index
                    }
                )
        return cov_map        

    @staticmethod
    def print_cov_map():
        for f, func in BBCovCoverageStats.COV_MAP.items():
            print(f"{f.file_name} | {f.name} : ")
            for bb in func:
                print(f"\t{bb.id} : {bb.coverage_index} : {bb.line_details}")

    @staticmethod
    def print_cov():
        print(BBCovCoverageStats.COV_MAP)

    @staticmethod
    def print_stats():
        for f, func in BBCovCoverageStats.COV_MAP.items():
            print(f"{f.file_name} | {f.name} : ")
            covered = 0
            total = 0
            for bb in func:
                if bb.coverage_index > 0:
                    covered += 1
            total = len(func)
            print(f"\t{covered} / {total} : {covered/total}")

    @staticmethod
    def print_summary(function):
        for f, func in BBCovCoverageStats.COV_MAP.items():
            if f.name == function:
                covered = 0
                total = 0
                for bb in func:
                    if bb.coverage_index > 0:
                        covered += 1
                total = len(func)
                print(f"{f.file_name} | {f.name} : ", end="")
                print(f"\t{covered} / {total} : {covered/total}")


def enable_comparison_mode():
    TracePCCoverageStats.set_cmp_mode(True)


def read_size(f):
    size = f.read(4)
    if size == b"":
        return None
    return struct.unpack("I", size)[0]


def read_uint32(f):
    size = f.read(4)
    if size == b"":
        return None
    return struct.unpack("I", size)[0]


def read_uint64(f):
    size = f.read(8)
    if size == b"":
        return None
    return struct.unpack("Q", size)[0]


def parse_cov_info_file(cov_info_file: pathlib.Path, mode: str = "tracepc"):
    assert (
        cov_info_file.exists() and cov_info_file.is_file()
    ), f"Coverage info file {cov_info_file} does not exist"

    cov_json = json.loads(cov_info_file.read_text())
    if mode == "tracepc":
        TracePCCoverageStats.init_cov_info(cov_json)
    elif mode == "bbcov":
        BBCovCoverageStats.init_cov_info(cov_json)


def parse_coverage_file(
    cov_file: pathlib.Path, mode: str = "tracepc", original_input: pathlib.Path = None
):
    assert (
        cov_file.exists() and cov_file.is_file()
    ), f"Coverage file {cov_file} does not exist"

    if mode == "tracepc":
        parse_tracepc_coverage_file(cov_file)
    elif mode == "bbcov":
        parse_bbcov_coverage_file(cov_file, original_input)
    else:
        raise NotImplementedError


def parse_tracepc_coverage_file(cov_file: pathlib.Path):
    f = open(cov_file, "rb")

    bbs = []
    while True:
        bb_id = read_uint32(f)
        if bb_id == None:
            break

        bbs.append(bb_id)

    # use the bbs to create the map
    TracePCCoverageStats.add_cov_map(bbs)


def parse_bbcov_coverage_file(
    cov_file: pathlib.Path, original_input: pathlib.Path = None
):
    
    cov_map = {}
    f = open(cov_file, "rb")

    while True:
        file_name_length = read_size(f)
        if file_name_length == None:
            break

        file_name = f.read(file_name_length)

        if not file_name:
            break

        func_map = {}
        num_functions = read_size(f)
        for _ in range(num_functions):
            function_name_length = read_size(f)
            function_name = f.read(function_name_length)

            if not function_name:
                break

            cov_array_len = read_size(f)
            cov_array = []
            for i in range(cov_array_len):
                cov_array.append(read_uint64(f))

            func_map[function_name] = cov_array
            log.debug(f"{function_name} : {cov_array}")

        cov_map[file_name] = func_map

    BBCovCoverageStats.add_cov_map(cov_map, original_input)


def print_files_covered_by_line(mode="bbcov", function="main", line=0):
    if mode == "tracepc":
        pass
    elif mode == "bbcov":
        files = BBCovCoverageStats.get_files_covering_line(function, line)
        print(files)
    else:
        raise NotImplementedError


def print_coverage_stats(mode="bbcov"):
    if mode == "tracepc":
        TracePCCoverageStats.print_stats()
    elif mode == "bbcov":
        BBCovCoverageStats.print_stats()
    else:
        raise NotImplementedError

def get_file_name(function : str):
    for f, func in BBCovCoverageStats.COV_MAP.items():
        if f.name == function:
            return f.file_name
    return None

def print_coverage_summary(mode="bbcov", function="main"):
    if mode == "tracepc":
        raise NotImplementedError
    elif mode == "bbcov":
        if function == "main":
            log.warning("SWITCHING MAIN to old_main_grill - for GRILLER !!!! IF NOT GRILLER pls fix")
            function = "old_main_grill"
        BBCovCoverageStats.print_summary(function)        
        return get_file_name(function)
    else:
        raise NotImplementedError

def dump_coverage_info(mode="bbcov", output_file=""):
    if mode == "tracepc":
        raise NotImplementedError
    elif mode == "bbcov":
        with open(output_file, "w") as f:
            f.write(json.dumps(BBCovCoverageStats.get_json_cov_map(), indent=4))
    else:
        raise NotImplementedError

def highlight_lines(function: str, sources: str, mode="bbcov", output_file=""):
    covered, uncovered, intersection = None, None, None
    if mode == "tracepc":
        if function == "main":
            log.warning("SWITCHING MAIN to old_main_grill - for GRILLER !!!! IF NOT GRILLER pls fix")
            function = "old_main_grill"
        covered, uncovered, intersection = TracePCCoverageStats.get_lines_covered(
            function
        )
    else:
        if function == "main":
            log.warning("SWITCHING MAIN to old_main_grill - for GRILLER !!!! IF NOT GRILLER pls fix")
            function = "old_main_grill"
        covered, uncovered, intersection = BBCovCoverageStats.get_lines_covered(
            function
        )

    fp = sys.stdout
    if output_file:
        fp = open(output_file, "w")

    if sources == None:
        print("NO SOURCES")
        return 

    for line in sources:
        if line.line in covered:
            fp.write(f"\033[92m{line.source}\033[0m")
        elif line.line in uncovered:
            fp.write(f"\033[91m{line.source}\033[0m")
        elif line.line in intersection:
            fp.write(f"\033[93m{line.source}\033[0m")
        else:
            fp.write(line.source)

def load_dumped_json_cov_map(json_file):
    """
    Loads coverage info from a dumped JSON file (from get_json_cov_map)
    and populates BBCovCoverageStats.COV_MAP.
    """
    with open(json_file, "r") as f:
        cov_json = json.load(f)
    BBCovCoverageStats.COV_MAP = {}
    for file_name, func_map in cov_json.items():
        for func_name, bb_list in func_map.items():
            fkey = Function(name=func_name, file_name=file_name)
            bb_objs = []
            for bb in bb_list:
                id = bb["Id"]
                linemap = [
                    LineDetails(line_obj["File"], line_obj["Line"])
                    for line_obj in bb["CovInfo"]
                ]
                covidx = bb.get("CovIndex", 0)
                bb_objs.append(CoverageDetails(covidx, id, linemap, []))
            BBCovCoverageStats.COV_MAP[fkey] = bb_objs
