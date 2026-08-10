# Python Quality

The package is maintained as a typed Python project. Public modules use type annotations and docstrings, and `src/euro_fsqca/py.typed` marks the installed package as PEP 561 compatible for downstream type checkers.

Run the local gates before merging:

```bash
make lint
make typecheck
make test
```

`make check` runs the same three gates in order. The repository CI runs the test suite across supported Python versions.

The CLI depends on Typer. `click` is constrained to the compatible `>=8.1,<8.3` range because newer Click releases changed option parsing behavior that Typer 0.12 does not handle correctly in this project.
