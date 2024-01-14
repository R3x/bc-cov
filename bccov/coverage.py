import pathlib
import struct


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

        cov_map[file_name] = func_map

    print(cov_map)
    return cov_map
