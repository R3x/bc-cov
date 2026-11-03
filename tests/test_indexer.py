"""Unit tests for the lazy libclang indexer (`bccov.indexer.CodebaseAnalyzer`)."""
import os

import clang.cindex
import pytest

from bccov.indexer import CodebaseAnalyzer

FOO_C = """int helper(int x) {
    return x + 1;
}

int foo(int a) {
    return helper(a) * 2;
}
"""
BAR_C = """static int bar(void) {
    return 7;
}
"""
BAR_H = "int bar_decl(void);\n"
OTHER_FOO_C = """int foo(int a) {
    return a;
}
"""


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "lib" / "sub").mkdir(parents=True)
    (tmp_path / "other").mkdir()
    (tmp_path / "lib" / "foo.c").write_text(FOO_C)
    (tmp_path / "lib" / "sub" / "bar.c").write_text(BAR_C)
    (tmp_path / "lib" / "sub" / "bar.h").write_text(BAR_H)
    (tmp_path / "other" / "foo.c").write_text(OTHER_FOO_C)
    (tmp_path / "other" / "notes.txt").write_text("foo bar")
    return tmp_path


def test_construction_indexes_paths_without_parsing(tree):
    a = CodebaseAnalyzer(str(tree))
    assert sorted(os.path.relpath(p, tree) for p in a.source_files) == [
        "lib/foo.c",
        "lib/sub/bar.c",
        "lib/sub/bar.h",
        "other/foo.c",
    ]
    assert a.cache == {}  # nothing parsed yet


def test_resolve_paths_prefers_longest_matching_suffix(tree):
    a = CodebaseAnalyzer(str(tree))
    lib_foo = str(tree / "lib" / "foo.c")
    other_foo = str(tree / "other" / "foo.c")
    assert sorted(a.resolve_paths("foo.c")) == sorted([lib_foo, other_foo])
    assert a.resolve_paths("lib/foo.c") == [lib_foo]
    assert a.resolve_paths("../../lib/foo.c") == [lib_foo]  # DWARF-style relative name
    assert a.resolve_paths("./other/foo.c") == [other_foo]
    assert a.resolve_paths(lib_foo) == [lib_foo]
    assert a.resolve_paths("bar.h") == [str(tree / "lib" / "sub" / "bar.h")]
    assert a.resolve_paths("missing.c") == []
    assert a.resolve_paths("") == []


def test_get_function_name_parses_only_the_asked_file(tree):
    a = CodebaseAnalyzer(str(tree))
    assert a.get_function_name("lib/foo.c", 6) == "foo"
    assert a.get_function_name("lib/foo.c", 2) == "helper"
    assert set(a.cache) == {str(tree / "lib" / "foo.c")}
    assert a.get_function_name("bar.c", 2) == "bar"
    assert a.get_function_name("bar.c", 99) is None
    with pytest.raises(Exception, match="Could not find function name"):
        a.get_function_name(str(tree / "lib" / "foo.c"), 4, throw_exception=True)


def test_get_function_source_with_file_hint(tree):
    a = CodebaseAnalyzer(str(tree))
    src = a.get_function_source("foo", "other/foo.c", output_mode=False)
    assert [s.line for s in src] == [1, 2, 3]
    assert src[0].file_path == str(tree / "other" / "foo.c")
    assert src[0].source.startswith("1:\tint foo(int a)")
    assert set(a.cache) == {str(tree / "other" / "foo.c")}


def test_get_function_source_without_file_hint_prefilters_by_text(tree):
    a = CodebaseAnalyzer(str(tree))
    src = a.get_function_source("bar", None, output_mode=False)
    assert src[0].file_path == str(tree / "lib" / "sub" / "bar.c")
    # only files that mention `bar` as a word were parsed (bar.c, bar.h; not foo.c)
    assert str(tree / "lib" / "foo.c") not in a.cache
    assert a.get_function_source("nope", None, output_mode=False) is None


def test_unloadable_file_is_skipped_not_fatal(tree, monkeypatch):
    a = CodebaseAnalyzer(str(tree))
    bad = str(tree / "lib" / "foo.c")
    real_parse = a.index.parse

    def parse(path, *args, **kwargs):
        if path == bad:
            raise clang.cindex.TranslationUnitLoadError("Error parsing translation unit.")
        return real_parse(path, *args, **kwargs)

    monkeypatch.setattr(a.index, "parse", parse)
    # the broken file resolves first for the bare basename but must not abort the lookup
    src = a.get_function_source("foo", "foo.c", output_mode=False)
    assert src[0].file_path == str(tree / "other" / "foo.c")
    assert bad in a.failed and bad not in a.cache
    assert a.load_file(bad) is False  # remembered, not re-parsed
    a.load_codebase()  # eager mode also survives it
    assert set(a.cache) == {
        str(tree / "lib" / "sub" / "bar.c"),
        str(tree / "lib" / "sub" / "bar.h"),
        str(tree / "other" / "foo.c"),
    }
