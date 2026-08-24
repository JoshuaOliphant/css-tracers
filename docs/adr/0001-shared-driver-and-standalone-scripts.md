# ADR-0001: A shared driver, and what that costs the standalone scripts

Status: accepted (2026-08-23)

## Context

Every tool re-implemented the same command-line driver: read `argv`, honour
`--help`/`-h`, print usage when given no arguments, open each path, report the
four file-error kinds to stderr, keep going after a bad path, print sorted
deduplicated class names, exit non-zero if any file failed. For `css-defs` that
driver was longer than the CSS parsing it wrapped.

Extracting it into `tools/tracer.py` collides with a stated design principle:
each tool is a single PEP 723 file, runnable via `uv run --script`. A script run
that way gets its own directory on `sys.path`, not the repository root, so
`from tools.tracer import run` fails — verified before choosing:

```
$ uv run --script tools/_probe_script.py
sys.path[0] = .../css-tracers/tools
absolute failed: ModuleNotFoundError No module named 'tools'
sibling (_probe_shared): shared-module-imported
```

A sibling import (`from tracer import run`) is the mirror image: it works under
`uv run --script` and breaks the installed console scripts, where `tools` is a
package and `tracer` is not top-level. A `try`/`except ImportError` over both
would work but leaves a branch no test run can cover, and the repo requires
100% branch coverage.

## Decision

The driver lives in `tools/tracer.py` and tools import it as
`from tools.tracer import run`. Each script's PEP 723 header declares the
repository itself as a dependency, resolved from the script's parent directory:

```
# dependencies = ["tinycss2", "css-tracers"]
#
# [tool.uv.sources]
# css-tracers = { path = "..", editable = true }
# ///
```

Both execution modes keep working, and their output is byte-identical:
`uv run css-defs ...` and `uv run --script tools/css_defs.py ...` produce the
same stdout, the same stderr and the same exit codes as the pre-driver tool for
a good file, a missing file, a directory and a non-UTF-8 file.

The dependency is editable and points at the checkout, so a script run picks up
local edits to the driver rather than a published build.

## Consequences

- A tool file is no longer self-contained. Copied on its own to another
  machine it will not run: `path = ".."` has to resolve to a checkout of this
  repository. `uv run --script` remains supported **from a clone**, which is how
  the README has always spelled it (`uv run --script tools/css_defs.py`). The
  README no longer calls the tools single self-contained files.
- A standalone run installs the whole project's dependency set, not just the
  one parser that tool needs. It is a cached, one-off cost per environment; the
  per-script `dependencies` list still names the direct parser dependency so the
  file keeps documenting what it actually needs.
- A git source (`css-tracers = { git = "..." }`) would restore copy-anywhere at
  the cost of a network fetch and of running a driver from GitHub HEAD rather
  than the working tree. Rejected for that skew, and because it cannot be proven
  green until the driver is already on `main`.
