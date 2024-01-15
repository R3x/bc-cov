from collections import namedtuple
import json
import pathlib
import struct

LineDetails = namedtuple("LineDetails", ["file_name", "line_no"])
CoverageDetails = namedtuple(
    "CoverageDetails", ["coverage_index", "id", "line_details"]
)
Function = namedtuple("Function", ["name", "file_name"])


class CoverageStats:
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
                CoverageStats.COV_MAP[f] = CoverageStats.cov_info_array_parse(
                    func_obj["BasicBlocks"]
                )

    @staticmethod
    def add_cov_map(cov_map):
        for file_name, func_map in cov_map.items():
            for func_name, cov_array in func_map.items():
                f = Function(name=func_name.decode(), file_name=file_name.decode())

                assert f in CoverageStats.COV_MAP, f"Function {f} not found in COV_MAP"
                assert len(cov_array) == len(
                    CoverageStats.COV_MAP[f]
                ), f"Coverage array length mismatch for {f}"

                for i in range(len(cov_array)):
                    assert (
                        i == CoverageStats.COV_MAP[f][i].id
                    ), f"Coverage index mismatch for {f} at index {i}"
                    CoverageStats.COV_MAP[f][i] = CoverageDetails(
                        coverage_index=max(
                            CoverageStats.COV_MAP[f][i].coverage_index, cov_array[i]
                        ),
                        id=CoverageStats.COV_MAP[f][i].id,
                        line_details=CoverageStats.COV_MAP[f][i].line_details,
                    )

    @staticmethod
    def get_function_coverage(name: str):
        for f, func in CoverageStats.COV_MAP.items():
            if f.name == name:
                return func
        return None

    @staticmethod
    def get_lines_covered(function: str):
        # TODO: not file sensitve
        stats = CoverageStats.get_function_coverage(function)
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
        return CoverageStats.COV_MAP

    @staticmethod
    def print_cov_map():
        for f, func in CoverageStats.COV_MAP.items():
            print(f"{f.file_name} | {f.name} : ")
            for bb in func:
                print(f"\t{bb.id} : {bb.coverage_index} : {bb.line_details}")

    @staticmethod
    def print_cov():
        print(CoverageStats.COV_MAP)


def read_size(f):
    size = f.read(4)
    if size == b"":
        return None
    return struct.unpack("I", size)[0]


def read_uint64(f):
    size = f.read(8)
    if size == b"":
        return None
    return struct.unpack("Q", size)[0]


def parse_cov_info_file(cov_info_file: pathlib.Path):
    assert (
        cov_info_file.exists() and cov_info_file.is_file()
    ), f"Coverage info file {cov_info_file} does not exist"

    cov_json = json.loads(cov_info_file.read_text())
    CoverageStats.init_cov_info(cov_json)


def parse_coverage_file(cov_file: pathlib.Path):
    assert (
        cov_file.exists() and cov_file.is_file()
    ), f"Coverage file {cov_file} does not exist"

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

    CoverageStats.add_cov_map(cov_map)


def print_coverage_stats():
    CoverageStats.print_cov_map()


def highlight_lines(function: str, sources: str):
    covered, uncovered, intersection = CoverageStats.get_lines_covered(function)
    for line in sources:
        if line.line in covered:
            print(f"\033[92m{line.source}\033[0m", end="")
        elif line.line in uncovered:
            print(f"\033[91m{line.source}\033[0m", end="")
        elif line.line in intersection:
            print(f"\033[93m{line.source}\033[0m", end="")
        else:
            print(line.source, end="")
