from collections import Counter
from dataclasses import dataclass, replace
from os.path import splitext

from sphinxlint.utils import PER_FILE_CACHES, _po2rst, hide_non_rst_blocks


@dataclass(frozen=True)
class PoEntry:
    """Identity of the translated PO entry containing a diagnostic."""

    msgctxt: str | None
    msgid: str
    msgid_plural: str


@dataclass(frozen=True)
class LintError:
    """A linting error found by one of the checkers"""

    filename: str
    line_no: int
    msg: str
    checker_name: str
    po_entry: PoEntry | None = None

    def __str__(self):
        return f"{self.filename}:{self.line_no}: {self.msg} ({self.checker_name})"


class CheckersOptions:
    """Configuration options for checkers."""

    max_line_length = 80

    @classmethod
    def from_argparse(cls, namespace):
        options = cls()
        options.max_line_length = namespace.max_line_length
        return options


def check_text(filename, text, checkers, options=None):
    if options is None:
        options = CheckersOptions()
    errors = []
    ext = splitext(filename)[1]
    checkers = {checker for checker in checkers if ext in checker.suffixes}
    lines = tuple(text.splitlines(keepends=True))
    if any(checker.rst_only for checker in checkers):
        lines_with_rst_only = hide_non_rst_blocks(lines)
    for check in checkers:
        if ext not in check.suffixes:
            continue
        for lno, msg in check(
            filename, lines_with_rst_only if check.rst_only else lines, options
        ):
            errors.append(LintError(filename, lno, msg, check.name))
    return errors


def check_file(filename, checkers, options: CheckersOptions = None):
    try:
        ext = splitext(filename)[1]
        if not any(ext in checker.suffixes for checker in checkers):
            return Counter()
        try:
            with open(filename, encoding="utf-8") as f:
                text = f.read()
            entries = {}
            if filename.endswith(".po"):
                text, entries = _po2rst(text)
        except OSError as err:
            return [f"{filename}: cannot open: {err}"]
        except UnicodeDecodeError as err:
            return [f"{filename}: cannot decode as UTF-8: {err}"]
        errors = check_text(filename, text, checkers, options)
        for index, error in enumerate(errors):
            if entry := entries.get(error.line_no):
                errors[index] = replace(
                    error,
                    po_entry=PoEntry(entry.msgctxt, entry.msgid, entry.msgid_plural),
                )
        return errors
    finally:
        for memoized_function in PER_FILE_CACHES:
            memoized_function.cache_clear()
