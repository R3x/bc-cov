import os
import pathlib
import re
from collections import namedtuple
from typing import List

import clang.cindex
from bccov import config as bccov_config
from bccov.utils import get_logger
from clang.cindex import Config

logger = get_logger(__name__, "INFO")

sources = namedtuple("sources", ["source", "line", "file_path"])

_LIBCLANG_CONFIGURED = False


def _configure_libclang():
    """Point clang.cindex at a libclang shared library.

    Historically this hardcoded LLVM-10 dev paths (`/home/r3x/...`,
    `/usr/lib/llvm-10/...`), which don't exist on an LLVM-16 toolchain. Derive
    the library from the configured `opt` binary (so it tracks LLVM_ROOT), with
    an env override and common fallbacks. Safe to call more than once.
    """
    global _LIBCLANG_CONFIGURED
    if _LIBCLANG_CONFIGURED:
        return

    file_candidates = []
    # 1. Explicit override.
    env_file = os.environ.get("LIBCLANG_LIBRARY_FILE")
    if env_file:
        file_candidates.append(env_file)
    # 2. Derived from the configured `opt` binary: <llvm_root>/lib/libclang.so*.
    opt = getattr(bccov_config, "LLVM_OPT", None)
    if opt and os.path.isabs(opt):
        llvm_lib = pathlib.Path(opt).resolve().parent.parent / "lib"
        file_candidates += [str(llvm_lib / "libclang.so.1"), str(llvm_lib / "libclang.so")]
    # 3. Common / legacy fallbacks.
    file_candidates += [
        "/usr/lib/llvm-16/lib/libclang.so.1",
        "/usr/lib/x86_64-linux-gnu/libclang-16.so.1",
        "/usr/lib/llvm-10/lib/libclang.so.1",
    ]
    for f in file_candidates:
        if f and pathlib.Path(f).is_file():
            Config.set_library_file(f)
            _LIBCLANG_CONFIGURED = True
            logger.info(f"Using libclang: {f}")
            return
    # 4. Directory-based legacy fallback.
    for d in ("/home/ubuntu/griller_workspace/tools/llvm-10/lib",
              "/home/r3x/llvm10/llvm-10.0.0.obj/lib"):
        if pathlib.Path(d).is_dir():
            Config.set_library_path(d)
            _LIBCLANG_CONFIGURED = True
            logger.info(f"Using libclang dir: {d}")
            return
    raise Exception(
        "Could not find libclang. Set LIBCLANG_LIBRARY_FILE, or install the "
        "LLVM toolchain libclang (e.g. /usr/lib/llvm-16/lib/libclang.so.1)."
    )


class CodebaseAnalyzer:
    """Lazy libclang index over a source tree.

    Construction only walks the tree once to build a cheap path index
    (basename -> candidate paths). A file is parsed with libclang the first
    time a lookup needs it (`get_function_name`, `get_function_source`), and a
    file libclang cannot load is logged and skipped instead of aborting the
    whole analysis. `load_codebase()` still parses everything eagerly for
    callers that want the old behaviour.
    """

    SOURCE_SUFFIXES = (".c", ".h")

    def __init__(self, codebase_path, eager=False):
        _configure_libclang()

        self.index = clang.cindex.Index.create()
        self.cache = {}  # parsed files: path -> {"tu", "functions"}
        self.failed = {}  # files libclang could not load: path -> error message
        self.codebase_path = os.path.abspath(codebase_path)
        self._paths = []  # every source file under codebase_path (absolute)
        self._by_basename = {}  # basename -> [absolute paths]
        self._build_path_index()
        if eager:
            self.load_codebase()

    # ------------------------------------------------------------------ index
    def _build_path_index(self):
        for root, dirs, files in os.walk(self.codebase_path):
            for file in files:
                if file.endswith(self.SOURCE_SUFFIXES):
                    file_path = os.path.join(root, file)
                    self._paths.append(file_path)
                    self._by_basename.setdefault(file, []).append(file_path)
        logger.debug(
            f"Indexed {len(self._paths)} source files under {self.codebase_path}"
        )

    @property
    def source_files(self):
        """Every `.c`/`.h` path under the codebase (parsed or not)."""
        return list(self._paths)

    def resolve_paths(self, file_name):
        """Candidate absolute paths for `file_name`.

        `file_name` may be absolute, relative to the codebase, relative to some
        compilation directory (`../lib/foo/bar.c`, as debug info records it) or
        a bare basename. Candidates share the basename; when `file_name`
        carries directory components, the candidates whose path ends with the
        longest run of those components win, so `lib/foo/bar.c` is preferred
        over another `bar.c` elsewhere in the tree.
        """
        if not file_name:
            return []
        file_name = str(file_name)
        if os.path.isabs(file_name):
            if file_name in self._by_basename.get(os.path.basename(file_name), []):
                return [file_name]
            if os.path.isfile(file_name):
                return [file_name]
        candidates = self._by_basename.get(os.path.basename(file_name), [])
        if len(candidates) <= 1:
            return list(candidates)
        # Rank by how many trailing path components agree with file_name
        # ("." / ".." / empty components carry no information).
        wanted = [
            c
            for c in os.path.normpath(file_name).split(os.sep)
            if c not in ("", ".", "..")
        ]
        best_score, best = -1, []
        for cand in candidates:
            parts = cand.split(os.sep)
            score = 0
            for w, p in zip(reversed(wanted), reversed(parts)):
                if w != p:
                    break
                score += 1
            if score > best_score:
                best_score, best = score, [cand]
            elif score == best_score:
                best.append(cand)
        return best

    # ---------------------------------------------------------------- parsing
    def load_codebase(self):
        """Eagerly parse every source file (the pre-lazy behaviour)."""
        for file_path in self._paths:
            logger.debug(f"Loading {file_path}")
            self.load_file(file_path)

    def load_file(self, file_path):
        """Parse `file_path` (idempotent). Returns True when it is indexed."""
        if file_path in self.cache:
            return True
        if file_path in self.failed:
            return False
        try:
            tu = self.index.parse(file_path)
        except clang.cindex.TranslationUnitLoadError as e:
            logger.warning(f"Skipping {file_path}: libclang could not load it ({e})")
            self.failed[file_path] = str(e)
            return False
        self.cache[file_path] = {
            "tu": tu,
            "functions": {},
        }
        self.extract_data(file_path)
        return True

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

    def _loaded_paths_for(self, file_name):
        """Resolve `file_name` and parse the candidates; yields indexed paths."""
        for path in self.resolve_paths(file_name):
            if self.load_file(path):
                yield path

    def _files_mentioning(self, identifier):
        """Cheap textual pre-filter: paths whose bytes contain `identifier` as a
        whole word. Used when a lookup has no file hint, so only files that can
        possibly define the function get parsed."""
        pattern = re.compile(rb"(?<![A-Za-z0-9_])" + re.escape(identifier.encode()) + rb"(?![A-Za-z0-9_])")
        for path in self._paths:
            try:
                with open(path, "rb") as f:
                    if pattern.search(f.read()):
                        yield path
            except OSError as e:
                logger.debug(f"Cannot read {path}: {e}")

    # ---------------------------------------------------------------- lookups
    def get_function_name(self, file_path, line_number, throw_exception=False):
        # file_path may be absolute, codebase-relative or a bare basename
        for path in self._loaded_paths_for(file_path):
            for function, node in self.cache[path]["functions"].items():
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

    def get_function_source(
        self, function_name, file_name, output_mode=True
    ) -> List[sources]:
        """
        :param function_name: Name of the function to find source of

        :return: The source of the function
        """
        # Handle the case there are multiple functions in the same file, we provide user with the choice for now
        functions = []
        if file_name:
            paths = list(self._loaded_paths_for(file_name))
        else:
            paths = [
                p for p in self._files_mentioning(function_name) if self.load_file(p)
            ]
        for file_path in paths:
            node = self.cache[file_path]["functions"].get(function_name)
            if node and node.is_definition():
                functions.append((file_path, node))

        if len(functions) == 0:
            print(f"Could not find function with the name {function_name}")
            return None

        node = None
        node = functions[0][1]
        file_path = functions[0][0]
        if len(functions) > 1:
            print(
                f"Found multiple functions with the name {function_name}. Please choose one:"
            )
            if output_mode:
                for i, (file_path, node) in enumerate(functions):
                    print(f"{i + 1}. {file_path}")
                choice = int(input("Enter your choice: "))
                node = functions[choice - 1][1]
                file_path = functions[choice - 1][0]

        start_line, end_line = node.extent.start.line, node.extent.end.line
        with open(file_path, "rb") as file:
            lines = file.readlines()
        # prepend each line with the line number and a tab
        new_lines = []
        for i in range(start_line, end_line + 1):
            new_lines.append(
                sources(f"{i}:\t{lines[i - 1].decode('latin-1')}", i, file_path)
            )

        return new_lines

DB = None


def create_code_database(path):
    global DB
    if DB == None:
        DB = CodebaseAnalyzer(path)


def get_function_source(function_name: str, file_name=None, output_mode=True):
    """
    Get the source code for a given function name

    :param function_name: Name of the function to find source of
    :type function_name: str

    :return: The source of the function
    :rtype: str
    """
    global DB
    return DB.get_function_source(function_name, file_name, output_mode)


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
