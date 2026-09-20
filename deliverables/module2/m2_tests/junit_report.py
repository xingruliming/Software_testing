"""Generate a JUnit XML report for the module 2 AI-output suite.

``run_tests.ps1`` invokes this helper, so results can be consumed by CI /
report tooling without parsing console text. The suite is executed exactly
once: the same result object drives both the console output and the XML.

Usage::

    python m2_tests/junit_report.py --output test_results/module2/run_x.xml \
        --start-dir m2_tests --pattern "test_m2_ai*.py" --log test_results/module2/run_x.log

The module discovery root (``-t``) is the current working directory, matching
the invocation used by ``run_tests.ps1`` (it runs from the module2 directory).

When ``--log`` is given, the same console text is also written to that file as
UTF-8. Writing the log here (rather than letting PowerShell capture the child
process output) keeps non-ASCII test names intact: Windows PowerShell 5.1
decodes a native process' stderr using the console ANSI codepage, which
double-encodes Chinese text.

``--header-file`` optionally names a UTF-8 file whose content is prepended to
the log; ``run_tests.ps1`` uses this to contribute the run banner.

Exit code: 0 when every test passes, 1 when there are failures, errors or
skips that the caller treats as significant (skips alone keep exit code 0).

Only the standard library is used, so no extra dependency is required.
"""

from __future__ import annotations

import argparse
import io
import sys
import unittest
from pathlib import Path


class _Tee:
    """Write the runner output to the real stdout and to an in-memory buffer."""

    def __init__(self, stream, buffer):
        self._stream = stream
        self._buffer = buffer

    def write(self, text):
        self._stream.write(text)
        self._buffer.write(text)
        return len(text)

    def flush(self):
        self._stream.flush()

    def isatty(self):
        return False


def build_suite(start_dir: str, pattern: str, top_level: str) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    return loader.discover(start_dir=start_dir, pattern=pattern, top_level_dir=top_level)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run module 2 tests and emit JUnit XML.")
    parser.add_argument("--output", required=True, help="Path of the JUnit XML file to write.")
    parser.add_argument("--start-dir", required=True, help="Discovery start directory, e.g. m2_tests")
    parser.add_argument("--pattern", default="test_m2_ai*.py",
                        help="unittest discovery pattern (default: test_m2_ai*.py)")
    parser.add_argument("--top-level", default=".",
                        help="unittest discovery top-level directory (default: current directory)")
    parser.add_argument("--log", default=None,
                        help="Optional path of a UTF-8 console log to write alongside the XML.")
    parser.add_argument("--header-file", default=None,
                        help="Optional UTF-8 file whose content is prepended to the --log output.")
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suite = build_suite(args.start_dir, args.pattern, args.top_level)

    buffer = io.StringIO()
    runner = unittest.TextTestRunner(verbosity=2, stream=_Tee(sys.stdout, buffer))
    result = runner.run(suite)

    _write_junit_xml(result, output_path, suite_name="module2-ai-output")

    if args.log:
        log_path = Path(args.log)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        header = ""
        if args.header_file:
            header_path = Path(args.header_file)
            if header_path.is_file():
                header = header_path.read_text(encoding="utf-8")

        log_path.write_text(header + buffer.getvalue(), encoding="utf-8", newline="")

    print(f"JUnit XML written: {output_path}")
    return 0 if result.wasSuccessful() else 1


def _write_junit_xml(result, output_path, suite_name: str) -> None:
    """Write a minimal, well-formed JUnit XML from a unittest result."""
    import xml.etree.ElementTree as ET

    testsuite = ET.Element(
        "testsuite",
        {
            "name": suite_name,
            "tests": str(result.testsRun),
            "failures": str(len(result.failures)),
            "errors": str(len(result.errors)),
            "skipped": str(len(result.skipped)),
        },
    )

    recorded = {test: ("failure", trace) for test, trace in result.failures}
    recorded.update({test: ("error", trace) for test, trace in result.errors})

    for test, (kind, trace) in recorded.items():
        case = ET.SubElement(
            testsuite,
            "testcase",
            {"classname": test.__class__.__name__, "name": test._testMethodName},
        )
        last_line = ""
        for line in reversed(trace.strip().splitlines()):
            if line.strip().startswith(("AssertionError", "Assertion", "Error")):
                last_line = line.strip()
                break
        if not last_line:
            last_line = trace.strip().splitlines()[-1] if trace.strip() else ""
        ET.SubElement(case, kind, {"message": last_line[:500], "type": kind})

    ET.ElementTree(testsuite).write(output_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    raise SystemExit(main())
