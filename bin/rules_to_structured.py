"""Extract numbered rule paragraphs from the comprehensive-rules markdown.

Produces one file per (chapter, section, subsection, ...) under
`data/rules/structured/_raw/`, named by the section number (e.g. `1.9.md`,
`4.6.4.md`). Each file contains the verbatim text of every numbered
paragraph under that section, in order, separated by blank lines.

Usage:
    .venv/bin/python bin/rules_to_structured.py
    .venv/bin/python bin/rules_to_structured.py path/to/rules.md [output_dir]
    .venv/bin/python bin/rules_to_structured.py --sections 1,2,4.6 output_dir
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.*\S)\s*$")

DEFAULT_MD = Path("data/rules/comprehensive-rules-2.2.0-en.md")
DEFAULT_OUT = Path("data/rules/structured/_raw")


def split_sections(md_text: str) -> dict[str, list[str]]:
    """Group numbered paragraphs by their longest-matching section number.

    Returns a dict from section number (e.g. '4.6.4') to a list of paragraph
    strings. A paragraph '4.6.4.1. ...' lives under section '4.6.4'.
    Sections present in the doc as headings but with no body paragraphs map
    to an empty list.

    The markdown wraps each long paragraph across multiple visual lines; we
    join them into one paragraph per rule, preserving internal newlines as
    spaces so the quoted text reads cleanly.
    """
    sections: dict[str, list[str]] = {}
    paragraphs: list[str] = []

    def flush() -> None:
        if paragraphs:
            joined = " ".join(p.strip() for p in paragraphs if p.strip())
            joined = re.sub(r"\s+", " ", joined).strip()
            paragraphs.clear()
            if joined:
                # Bucket under parent section.
                m = PREFIX_RE.match(joined)
                if m:
                    number = m.group(1)
                    parent = ".".join(number.split(".")[:-1])
                    if parent:
                        sections.setdefault(parent, []).append(joined)
                        sections.setdefault(number, sections.get(number, []))

    for raw_line in md_text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if PREFIX_RE.match(line):
            # New numbered paragraph: flush the previous one first.
            flush()
            paragraphs.append(line)
        else:
            # Continuation line of the current paragraph.
            if paragraphs:
                paragraphs.append(line)
    flush()
    return sections


def section_slug(number: str) -> str:
    return number.replace(".", "_")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "md",
        nargs="?",
        type=Path,
        default=DEFAULT_MD,
        help="Path to the comprehensive rules markdown.",
    )
    parser.add_argument(
        "out",
        nargs="?",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory for raw per-section files.",
    )
    parser.add_argument(
        "--sections",
        help="Comma-separated list of section numbers to write (default: all).",
    )
    args = parser.parse_args(argv)

    if not args.md.is_file():
        print(f"error: {args.md} not found", file=sys.stderr)
        return 1

    md_text = args.md.read_text(encoding="utf-8")
    sections = split_sections(md_text)

    only: set[str] | None = None
    if args.sections:
        only = {s.strip() for s in args.sections.split(",") if s.strip()}

    args.out.mkdir(parents=True, exist_ok=True)
    written = 0
    for number in sorted(sections, key=lambda n: tuple(int(x) for x in n.split("."))):
        if only is not None and number not in only:
            continue
        out_path = args.out / f"{section_slug(number)}.md"
        body = "\n\n".join(sections[number])
        out_path.write_text(body + "\n", encoding="utf-8")
        written += 1

    print(f"wrote {written} section file(s) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
