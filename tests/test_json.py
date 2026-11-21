import json
import subprocess
import sys

import polib
import pytest

from sphinxlint import LintError, check_file
from sphinxlint.checkers import all_checkers
from sphinxlint.cli import main, print_errors


def run_json(capsys, *args):
    status = main(["sphinx-lint", "--format", "json", *map(str, args)])
    out, err = capsys.readouterr()
    assert err == ""
    return status, json.loads(out)


def test_json_clean_file(tmp_path, capsys):
    path = tmp_path / "clean.rst"
    path.write_text("Clean text.\n", encoding="utf-8")
    status, report = run_json(capsys, path)
    assert status == 0
    assert report == {"version": 1, "diagnostics": [], "errors": []}


def test_json_diagnostic(tmp_path, capsys):
    path = tmp_path / "zażółć 'quoted'.rst"
    path.write_text("First line.\nTrailing space. \n", encoding="utf-8")
    status, report = run_json(capsys, path)
    assert status == 1
    assert report == {
        "version": 1,
        "diagnostics": [
            {
                "filename": str(path),
                "line_no": 2,
                "msg": "trailing whitespace",
                "checker_name": "trailing-whitespace",
                "po_entry": None,
            }
        ],
        "errors": [],
    }


def test_json_escaped_filename(capsys):
    filename = 'zażółć "quoted"\\file.rst'
    error = LintError(filename, 2, "trailing whitespace", "trailing-whitespace")
    assert print_errors([error], "json") == 1
    out, err = capsys.readouterr()
    assert err == ""
    assert json.loads(out)["diagnostics"][0]["filename"] == filename


def test_json_checker_selection_and_options(tmp_path, capsys):
    path = tmp_path / "long.rst"
    path.write_text("This line exceeds the configured length.\n", encoding="utf-8")
    status, report = run_json(capsys, "--disable", "all", path)
    assert status == 0
    assert report["diagnostics"] == []
    status, report = run_json(
        capsys,
        "--disable",
        "all",
        "--enable",
        "line-too-long",
        "--max-line-length",
        "20",
        path,
    )
    assert status == 1
    assert [d["checker_name"] for d in report["diagnostics"]] == ["line-too-long"]


def test_json_missing_path(tmp_path, capsys):
    path = tmp_path / "missing.rst"
    status, report = run_json(capsys, path)
    assert status == 2
    assert report == {
        "version": 1,
        "diagnostics": [],
        "errors": [f"Error: path {path} does not exist"],
    }


def test_json_file_failure_with_sorting(tmp_path, capsys):
    bad = tmp_path / "bad.rst"
    bad.write_bytes(b"\xff")
    lint = tmp_path / "lint.rst"
    lint.write_text("Trailing space. \n", encoding="utf-8")
    status, report = run_json(
        capsys, "--sort-by", "filename,line,error_type", bad, lint
    )
    assert status == 1
    assert len(report["diagnostics"]) == 1
    assert len(report["errors"]) == 1
    assert report["errors"][0].startswith(f"{bad}: cannot decode as UTF-8:")


def test_json_cannot_list_checkers(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["sphinx-lint", "--format", "json", "--list"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "--format json cannot be used with --list" in err


def test_json_po_entry_identity(tmp_path, capsys):
    catalog = polib.POFile()
    # The generated translation extends past the next entry's original line
    # number. Mapping must follow po2rst's layout rather than PO source lines.
    catalog.append(polib.POEntry(msgid="First source", msgstr="Good\n" * 12 + "Bad \n"))
    catalog.append(
        polib.POEntry(msgctxt="button", msgid="Open", msgstr="Otwórz \nAgain \n")
    )
    catalog.append(polib.POEntry(msgid="Open", msgstr="Clean"))
    catalog.append(polib.POEntry(msgid="Fuzzy", msgstr="Bad ", flags=["fuzzy"]))
    catalog.append(polib.POEntry(msgid="Untranslated", msgstr=""))
    catalog.append(polib.POEntry(msgid="Obsolete", msgstr="Bad ", obsolete=True))
    path = tmp_path / "guide.po"
    first = catalog.pop(0)
    path.write_text(
        'msgid "First source"\nmsgstr '
        + json.dumps(first.msgstr)
        + "\n\n"
        + "\n".join(str(entry) for entry in catalog),
        encoding="utf-8",
    )

    status, report = run_json(capsys, "--sort-by", "line", path)
    assert status == 1
    assert report["errors"] == []
    diagnostics = report["diagnostics"]
    assert len(diagnostics) == 3
    assert [d["po_entry"] for d in diagnostics] == [
        {"msgctxt": None, "msgid": "First source", "msgid_plural": ""},
        {"msgctxt": "button", "msgid": "Open", "msgid_plural": ""},
        {"msgctxt": "button", "msgid": "Open", "msgid_plural": ""},
    ]
    assert diagnostics[1]["line_no"] > polib.pofile(str(path))[1].linenum
    failures = check_file(str(path), [all_checkers["trailing-whitespace"]])
    assert {f.po_entry.msgid for f in failures} == {"First source", "Open"}
    assert all(
        str(f).endswith("trailing whitespace (trailing-whitespace)") for f in failures
    )


def test_json_parallel_matches_serial(tmp_path):
    for index in range(8):
        (tmp_path / f"{index}.rst").write_text("Bad \nWorse \n", encoding="utf-8")
    catalog = polib.POFile()
    catalog.append(polib.POEntry(msgid="Source", msgstr="Bad "))
    catalog.save(str(tmp_path / "guide.po"))
    command = [
        sys.executable,
        "-m",
        "sphinxlint",
        "--format",
        "json",
        "--sort-by",
        "filename,line,error_type",
        str(tmp_path),
    ]
    reports = []
    for jobs in (1, 2):
        result = subprocess.run(
            [*command, "--jobs", str(jobs)], capture_output=True, text=True
        )
        assert result.returncode == 1
        assert result.stderr == ""
        reports.append(json.loads(result.stdout))
    assert reports[0] == reports[1]
    assert len(reports[0]["diagnostics"]) == 17
