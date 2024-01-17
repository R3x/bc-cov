from typing import List
from collections import namedtuple
import os

import clang.cindex

from bccov.utils import get_logger

logger = get_logger(__name__, "DEBUG")

sources = namedtuple("sources", ["source", "line", "file_path"])


class CodebaseAnalyzer:
    def __init__(self, codebase_path):
        self.index = clang.cindex.Index.create()
        self.cache = {}  # Cache to store indexes and extracted data for each file
        self.codebase_path = codebase_path
        self.load_codebase()

    def load_codebase(self):
        for root, dirs, files in os.walk(self.codebase_path):
            for file in files:
                if file.endswith(".c") or file.endswith(".h"):
                    file_path = os.path.join(root, file)
                    logger.debug(f"Loading {file_path}")
                    self.load_file(file_path)

    def load_file(self, file_path):
        tu = self.index.parse(file_path)
        self.cache[file_path] = {
            "tu": tu,
            "functions": {},
        }
        self.extract_data(file_path)

    def extract_data(self, file_path):
        tu = self.cache[file_path]["tu"]
        for node in tu.cursor.walk_preorder():
            if node.location.file is not None and node.location.file.name == file_path:
                if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                    self.cache[file_path]["functions"][node.spelling] = node
                # elif node.kind in [clang.cindex.CursorKind.STRUCT_DECL, clang.cindex.CursorKind.UNION_DECL, clang.cindex.CursorKind.TYPEDEF_DECL, clang.cindex.CursorKind.ENUM_DECL]:
                #     self.cache[file_path]['types'][node.spelling] = node
                # elif node.kind == clang.cindex.CursorKind.VAR_DECL:
                #     self.cache[file_path]['globals'][node.spelling] = node

    def get_function_name(self, file_path, line_number, throw_exception=False):
        # check if the file path is in the cache, can happen when the file path is a basename
        abs_file_path = os.path.abspath(file_path)
        if file_path not in self.cache:
            for paths in self.cache.keys():
                if os.path.basename(paths) == file_path:
                    abs_file_path = paths
                    break

        for function, node in self.cache[abs_file_path]["functions"].items():
            if node.extent.start.line <= line_number <= node.extent.end.line:
                return function

        if throw_exception:
            with open(file_path, "r") as file:
                lines = file.readlines()
            raise Exception(
                f'Could not find function name for {file_path}:{line_number} : Contents are - {"".join(lines[line_number - 1:line_number + 1])}'
            )
        else:
            return None

    def get_function_source(self, function_name) -> List[sources]:
        """
        :param function_name: Name of the function to find source of

        :return: The source of the function
        """
        for file_path, data in self.cache.items():
            node = data["functions"].get(function_name)
            if node and node.is_definition():
                start_line, end_line = node.extent.start.line, node.extent.end.line
                with open(file_path, "rb") as file:
                    lines = file.readlines()
                # prepend each line with the line number and a tab
                new_lines = []
                for i in range(start_line, end_line + 1):
                    new_lines.append(
                        sources(
                            f"{i}:\t{lines[i - 1].decode('latin-1')}", i - 1, file_path
                        )
                    )

                return new_lines


DB = None


def create_code_database(path):
    global DB
    DB = CodebaseAnalyzer(path)


def get_function_source(function_name: str):
    """
    Get the source code for a given function name

    :param function_name: Name of the function to find source of
    :type function_name: str

    :return: The source of the function
    :rtype: str
    """
    global DB
    return DB.get_function_source(function_name)


def get_function_from_line(filename: str, line: int):
    """
    Get the function name from a given filename and line number

    :param filename: Name of the file to find function in
    :type filename: str
    :param line: Line number to find function at
    :type line: int

    :return: The name of the function
    :rtype: str
    """
    global DB
    return DB.get_function_name(filename, line, throw_exception=True)


def main():
    # Usage:
    codebase_path = "/home/r3x/griller_targets/lighttpd/lighttpd1.4"
    analyzer = CodebaseAnalyzer(codebase_path)
    file_path = "/home/r3x/griller_targets/lighttpd/lighttpd1.4/src/lemon.c"
    line_number = 159
    function_name = "fdevent_fcntl_set_nb_cloexec"
    type_name = "server_socket"
    var_name = "datestrs"

    print(analyzer.get_function_name(file_path, line_number))
    print(analyzer.get_function_source(function_name))


if __name__ == "__main__":
    main()
