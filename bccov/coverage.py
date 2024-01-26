from collections import namedtuple
import json
import pathlib
import struct

LineDetails = namedtuple("LineDetails", ["file_name", "line_no"])
CoverageDetails = namedtuple(
    "CoverageDetails", ["coverage_index", "id", "line_details"]
)
Function = namedtuple("Function", ["name", "file_name"])


class TracePCCoverageStats:
    COV_MAP = {}
    ORDER = {}
    Counter = 0

    @staticmethod
    def init_cov_info(cov_info: dict):
        for bb_obj in cov_info["BasicBlock"]:
            id = bb_obj["Id"]
            linemap = []
            for line_obj in bb_obj["Coverage"]:
                linemap.append(LineDetails(line_obj["File"], line_obj["Line"]))
            TracePCCoverageStats.COV_MAP[id] = CoverageDetails(0, id, linemap)

    @staticmethod
    def add_cov_map(cov_map, id=None):

        for bb_id in cov_map:
            assert (
                bb_id in TracePCCoverageStats.COV_MAP
            ), f"BasicBlock {bb_id} not found in COV_MAP"

            if TracePCCoverageStats.COV_MAP[bb_id].coverage_index == 0:
                TracePCCoverageStats.COV_MAP[bb_id] = CoverageDetails(
                    1, bb_id, TracePCCoverageStats.COV_MAP[bb_id].line_details
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
            parsed_array.append(CoverageDetails(0, id, linemap))
        return parsed_array

    @staticmethod
    def init_cov_info(cov_info: dict):
        for file_name, func_map in cov_info.items():
            for func_obj in func_map:
                f = Function(name=func_obj["Function"], file_name=file_name)
                BBCovCoverageStats.COV_MAP[f] = BBCovCoverageStats.cov_info_array_parse(
                    func_obj["BasicBlocks"]
                )

    @staticmethod
    def add_cov_map(cov_map):
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
                    BBCovCoverageStats.COV_MAP[f][i] = CoverageDetails(
                        coverage_index=max(
                            BBCovCoverageStats.COV_MAP[f][i].coverage_index,
                            cov_array[i],
                        ),
                        id=BBCovCoverageStats.COV_MAP[f][i].id,
                        line_details=BBCovCoverageStats.COV_MAP[f][i].line_details,
                    )

    @staticmethod
    def get_function_coverage(name: str):
        for f, func in BBCovCoverageStats.COV_MAP.items():
            if f.name == name:
                return func
        return None

    @staticmethod
    def get_lines_covered(function: str):
        # TODO: not file sensitve
        stats = BBCovCoverageStats.get_function_coverage(function)
        if stats == None:
            return []
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


def parse_coverage_file(cov_file: pathlib.Path, mode: str = "tracepc"):
    assert (
        cov_file.exists() and cov_file.is_file()
    ), f"Coverage file {cov_file} does not exist"

    if mode == "tracepc":
        parse_tracepc_coverage_file(cov_file)
    elif mode == "bbcov":
        parse_bbcov_coverage_file(cov_file)
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


def parse_bbcov_coverage_file(cov_file: pathlib.Path):
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
            print(f"{function_name} : {cov_array}")

        cov_map[file_name] = func_map

    BBCovCoverageStats.add_cov_map(cov_map)


def print_coverage_stats(mode="bbcov"):
    if mode == "tracepc":
        TracePCCoverageStats.print_stats()
    elif mode == "bbcov":
        BBCovCoverageStats.print_stats()
    else:
        raise NotImplementedError


def highlight_lines(function: str, sources: str, mode="bbcov"):
    covered, uncovered, intersection = None, None, None
    if mode == "tracepc":
        covered, uncovered, intersection = TracePCCoverageStats.get_lines_covered(
            function
        )
    else:
        covered, uncovered, intersection = BBCovCoverageStats.get_lines_covered(
            function
        )
    for line in sources:
        if line.line in covered:
            print(f"\033[92m{line.source}\033[0m", end="")
        elif line.line in uncovered:
            print(f"\033[91m{line.source}\033[0m", end="")
        elif line.line in intersection:
            print(f"\033[93m{line.source}\033[0m", end="")
        else:
            print(line.source, end="")
