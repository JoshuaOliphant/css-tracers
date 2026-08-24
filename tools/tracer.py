# ABOUTME: Shared command-line driver for the class-tracing tools.
# ABOUTME: Owns argv parsing, help, file reading, error reporting, output and exit code.

"""The driver every tracer tool runs on.

A tool declares its name, its help text, whether it reads text or bytes, and
how it extracts class names from one file's contents. Everything else — the
command line, reading the files, reporting the ones that failed, printing the
class names and choosing the exit code — happens here.
"""

import sys


def _open(path, binary):
    if binary:
        return open(path, "rb")
    return open(path, encoding="utf-8")


def run(*, name, doc, extract, binary=False):
    """Run one tracer tool over the paths in sys.argv.

    ``extract`` takes one file's contents — text, or bytes when ``binary`` —
    and returns the set of class names found in it.
    """
    if "--help" in sys.argv or "-h" in sys.argv:
        print(doc.strip())
        sys.exit(0)

    paths = sys.argv[1:]
    if not paths:
        print(f"Usage: {name} <file>...", file=sys.stderr)
        sys.exit(1)

    classes = set()
    failed = False
    for path in paths:
        try:
            with _open(path, binary) as f:
                classes |= extract(f.read())
        except FileNotFoundError:
            print(f"{name}: {path}: No such file", file=sys.stderr)
            failed = True
        except IsADirectoryError:
            print(f"{name}: {path}: Is a directory", file=sys.stderr)
            failed = True
        except UnicodeDecodeError:
            print(f"{name}: {path}: Not valid UTF-8 text (binary file?)", file=sys.stderr)
            failed = True
        except OSError as exc:
            print(f"{name}: {path}: {exc}", file=sys.stderr)
            failed = True

    for cls in sorted(classes):
        print(cls)

    if failed:
        sys.exit(1)
