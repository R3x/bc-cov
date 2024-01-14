import pathlib
import struct


class CoverageStats:

    COV_MAP = {}

    @staticmethod
    def add_cov_map(cov_map):
        for file_name, func_map in cov_map.items():
            if file_name not in CoverageStats.COV_MAP:
                CoverageStats.COV_MAP[file_name] = {}
            for func_name, cov_array in func_map.items():
                if func_name not in CoverageStats.COV_MAP[file_name]:
                    CoverageStats.COV_MAP[file_name][func_name] = [0] * len(cov_array)
                assert len(cov_array) == len(
                    CoverageStats.COV_MAP[file_name][func_name]
                )
                for i in range(len(cov_array)):
                    CoverageStats.COV_MAP[file_name][func_name][i] = max(
                        CoverageStats.COV_MAP[file_name][func_name][i], cov_array[i]
                    )

    @staticmethod
    def get_cov_map():
        return CoverageStats.COV_MAP

    @staticmethod
    def print_cov_map():
        for file_name, func_map in CoverageStats.COV_MAP.items():
            print(file_name)
            for func_name, cov_array in func_map.items():
                print(f"\t{func_name} : ", end="")
                for i in range(len(cov_array)):
                    print(f"{cov_array[i]}", end=" ")


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
