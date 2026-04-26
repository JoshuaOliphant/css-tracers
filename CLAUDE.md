# css-tracers — Claude project rules

## Rule: 100% test coverage is required

Every change to code under `tools/` must keep line **and** branch coverage at
exactly 100%. This is enforced by `pytest-cov` via the `--cov-fail-under=100`
flag wired into `[tool.pytest.ini_options]` in `pyproject.toml`, so a coverage
regression fails the test suite.

What this means in practice:

- When you add or modify code in `tools/`, you must add or update tests in
  `tests/` so every new branch is exercised.
- When `pytest` reports an uncovered line or branch, fix it before claiming
  the task is done. Do not lower the threshold, do not add blanket
  `# pragma: no cover`, and do not delete tests to make the bar easier.
- If a branch is genuinely unreachable (defensive guards against impossible
  states, etc.), prefer **deleting the dead code** over excluding it from
  coverage. The README's design principles favor small, direct tools — dead
  code works against that.
- Only use `# pragma: no cover` when the code is *intentionally* unreachable
  in tests (for example, `if __name__ == "__main__":` blocks, which are
  already excluded globally via `[tool.coverage.report]`).

## Running the tests

```bash
uv sync --all-extras           # install dev deps including pytest-cov
uv run pytest                  # runs tests with coverage; fails under 100%
```

The `addopts` in `pyproject.toml` already pass `--cov=tools
--cov-report=term-missing --cov-fail-under=100`, so a bare `uv run pytest` is
the canonical command — both locally and in CI.

## Project layout

- `tools/` — the four standalone tools (`css_defs`, `jinja_refs`, `js_refs`,
  `py_refs`). Each is a single module exposing a `main()` entry point and the
  pure functions it composes. Tests should target the pure functions
  directly, then drive `main()` through `monkeypatch.setattr("sys.argv", ...)`
  for the CLI surface.
- `tests/` — one `test_<tool>.py` per tool. Keep them organized that way.

## Writing testable code

If a piece of code is hard to cover with a test, treat that as a signal to
refactor — extract a pure function, drop a defensive guard that can never
fire, or simplify the control flow. Reach for the test first; only then
consider whether the code itself should change.
