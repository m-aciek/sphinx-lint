# Sphinx Lint

[![PyPI](https://img.shields.io/pypi/v/sphinx-lint)
 ![Monthly downloads](https://img.shields.io/pypi/dm/sphinx-lint)
 ![Supported Python Version](https://img.shields.io/pypi/pyversions/sphinx-lint.svg)
](https://pypi.org/project/sphinx-lint)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/sphinx-contrib/sphinx-lint/tests.yml?branch=main)](https://github.com/sphinx-contrib/sphinx-lint/actions)

Sphinx Lint is based on [rstlint.py from
CPython](https://github.com/python/cpython/blob/e0433c1e7/Doc/tools/rstlint.py).


## What is Sphinx Lint, what is it not?

Sphinx Lint should:

- be reasonably fast so it's comfortable to use as a linter in your editor.
- be usable on a single file.
- not give any false positives (probably a utopia, but let's try).
- not spend too much effort finding errors that sphinx-build already finds (or can easily find).
- focus on finding errors that are **not** visible to sphinx-build.


## Using Sphinx Lint

Here are some example invocations of Sphinx Lint from the command line:

```sh
sphinx-lint           # check all dirs and files
sphinx-lint file.rst  # check a single file
sphinx-lint docs      # check a directory
sphinx-lint -i venv   # ignore a file/directory
sphinx-lint -h        # for more options
```

Sphinx Lint can also be used via [pre-commit](https://pre-commit.com).
We recommend using a configuration like this:

```yaml
  - repo: https://github.com/sphinx-contrib/sphinx-lint
    rev: LATEST_SPHINXLINT_RELEASE_TAG
    hooks:
      - id: sphinx-lint
```


### Machine-readable output

Use `--format json` to write a JSON report to standard output:

```sh
sphinx-lint --format json --sort-by filename,line,error_type docs > lint.json
```

The report has a schema version, diagnostics, and file or path errors:

```json
{
  "version": 1,
  "diagnostics": [
    {
      "filename": "docs/guide.rst",
      "line_no": 12,
      "msg": "trailing whitespace",
      "checker_name": "trailing-whitespace",
      "po_entry": null
    }
  ],
  "errors": []
}
```

`line_no` is one-based, or 0 for a diagnostic about the whole file.
Paths follow the same conventions as text output.
`checker_name` is the name accepted by `--enable` and `--disable`.
For diagnostics in translated PO entries, `po_entry` contains `msgctxt`,
`msgid`, and `msgid_plural`, so consumers can identify the affected entry
without reconstructing the extracted translation's line numbers. For example:

```json
{"msgctxt": "button", "msgid": "Open", "msgid_plural": ""}
```

Absent contexts are `null`; absent plural message IDs are empty strings.
`po_entry` is `null` when a diagnostic cannot be associated with an entry,
including for non-PO files. PO line numbers refer to the extracted translations,
as in text output, and can differ from physical catalog line numbers.
Only the translated entries checked by Sphinx Lint are included; fuzzy,
untranslated, and obsolete entries are skipped.

A clean run produces empty `diagnostics` and `errors` arrays. `errors` contains
strings describing files or paths that could not be checked. Exit status is
unchanged: 0 for a clean run, 1 for diagnostics or file errors, and 2 for invalid
arguments or missing paths. Consumers should check both the exit status and
`errors` before treating a report as a completed check. Argument errors still
use standard error; `--list` cannot be combined with `--format json`.
Use `--sort-by` when you need a predictable order across parallel runs.

Python integrations can also use `check_file()` directly. It returns
`LintError` objects with the same fields, including `po_entry` (a `PoEntry`
object or `None`). File errors are returned as strings. `check_text()` returns
diagnostics with `po_entry=None` because it checks text without parsing a catalog.


### Selecting checks

Most checks are enabled by default. The following checks are available but disabled by default:

| Check | Description |
| --- | --- |
| `default-role` | Reports default roles, such as `` `print` ``, which many projects allow. |
| `leaked-markup` | Checks built HTML files for leaked reStructuredText markup. |
| `line-too-long` | Reports lines longer than 80 characters by default; use `--max-line-length` to change the limit. |
| `triple-backticks` | Reports triple backticks, such as `` ```text``` ``, which are valid but uncommon reStructuredText. |

Use `--enable` to opt into one or more checks:

```sh
sphinx-lint --enable=default-role docs
sphinx-lint --enable=default-role,line-too-long docs
sphinx-lint --enable=all docs
```

In a pre-commit configuration, pass the option using `args`:

```yaml
  - repo: https://github.com/sphinx-contrib/sphinx-lint
    rev: LATEST_SPHINXLINT_RELEASE_TAG
    hooks:
      - id: sphinx-lint
        args: [--enable=default-role]
```

Run `sphinx-lint --list` to see every available check and whether it is enabled. You can combine `--list` with `--enable` and `--disable` to preview the resulting selection.


## Known issues

Currently Sphinx Lint can't work with tables, there's no understanding
of how `linesplit` works in tables, like:

```rst
   +-----------------------------------------+-----------------------------+---------------+
   | Method                                  | Checks that                 | New in        |
   +=========================================+=============================+===============+
   | :meth:`assertEqual(a, b)                | ``a == b``                  |               |
   | <TestCase.assertEqual>`                 |                             |               |
   +-----------------------------------------+-----------------------------+---------------+
```

as Sphinx Lint works line by line it will inevitably think the `:meth:` role is not closed properly.

To avoid false positives, some rules are skipped if we're in a table.


## Contributing

A quick way to test if some syntax is valid from a pure
reStructuredText point of view, one case use `docutils`'s `pseudoxml`
writer, like:

```text
$ docutils --writer=pseudoxml tests/fixtures/xpass/role-in-code-sample.rst
<document source="tests/fixtures/xpass/role-in-code-sample.rst">
    <paragraph>
        Found in the pandas documentation, this is valid:
    <bullet_list bullet="*">
        <list_item>
            <paragraph>
                A pandas class (in the form
                <literal>
                    :class:`pandas.Series`
                )
        <list_item>
            <paragraph>
                A pandas method (in the form
                <literal>
                    :meth:`pandas.Series.sum`
                )
        <list_item>
            <paragraph>
                A pandas function (in the form
                <literal>
                    :func:`pandas.to_datetime`
                )
    <paragraph>
        it's documenting roles using code samples (double backticks).
```


## Releasing

1. Make sure that the [CI tests pass](https://github.com/sphinx-contrib/sphinx-lint/actions)
   and optionally double-check locally with "friends projects" by running:

       sh download-more-tests.sh
       python -m pytest
2. Go on the [Releases page](https://github.com/sphinx-contrib/sphinx-lint/releases)
3. Click "Draft a new release"
4. Click "Choose a tag"
5. Type the next vX.Y.Z version and select "Create new tag: vX.Y.Z on publish"
6. Leave the "Release title" blank (it will be autofilled)
7. Click "Generate release notes" and amend as required
8. Click "Publish release"
9. Check the tagged
   [GitHub Actions build](https://github.com/sphinx-contrib/sphinx-lint/actions/workflows/deploy.yml)
   has [deployed to PyPI](https://pypi.org/project/sphinx-lint/#history)


## License

As this script was in the CPython repository the license is the Python
Software Foundation Licence Version 2, see the LICENSE file for a full
version.
