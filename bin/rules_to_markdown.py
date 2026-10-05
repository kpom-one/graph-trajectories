"""Convert the Disney Lorcana Comprehensive Rules PDF to Markdown.

Usage:
    .venv/bin/python bin/rules_to_markdown.py
    .venv/bin/python bin/rules_to_markdown.py path/to/rules.pdf [output.md]

The PDF is a flat, numbered document (1., 1.1., 1.1.1., ...). We extract text
with pypdf's layout mode so each visual line keeps its indent, then detect
numbered headings vs. body paragraphs from the leading indent and prefix.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

# Numbered heading prefixes.
H1_RE = re.compile(r"^(\d+)\.\s+(.+)$")
H2_RE = re.compile(r"^(\d+\.\d+)\.\s+(.+)$")
H3_RE = re.compile(r"^(\d+\.\d+\.\d+)\.\s+(.+)$")
H4_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\.\s+(.+)$")

# Footer fragments that recur on every page. The PDF sometimes puts the
# footer phrase and the page number on the same physical line (cover and
# contents pages), so we strip them anywhere in the line.
FOOTER_FRAGMENTS = (
    "disneylorcana.com",
    "©Disney",
    "©Disney/Pixar",
    'Based on the "Winnie the Pooh" works by A. A. Milne',
    'Based on the "Winnie the Pooh" works by A.A. Milne',
    "E.H. Shepard.",
    "E. H. Shepard.",
)
PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")


def strip_footer(line: str) -> str:
    # Preserve leading whitespace so we can still detect paragraph indents.
    leading = len(line) - len(line.lstrip(" "))
    body = line.lstrip(" ")
    for frag in FOOTER_FRAGMENTS:
        body = body.replace(frag, "")
    # Strip a bare trailing page number left behind after footer removal.
    body = PAGE_NUMBER_RE.sub("", body)
    body = body.rstrip()
    # Collapse interior runs of whitespace.
    body = re.sub(r"\s{2,}", " ", body)
    return (" " * leading) + body


def classify_heading(line: str) -> tuple[int, str, str] | None:
    """Return (level, number, title) if `line` is a real section heading.

    Distinguishes a heading like "1.1.    General" (short, no body text)
    from a body paragraph like "1.1.1.   The Disney Lorcana TCG is a game..."
    by length and punctuation: headings are short and don't end with a
    sentence terminator.
    """
    stripped = line.lstrip()
    # Try deepest first so 1.1.1.1. doesn't match the 1. regex.
    for level, regex in ((4, H4_RE), (3, H3_RE), (2, H2_RE), (1, H1_RE)):
        m = regex.match(stripped)
        if m:
            title = m.group(2).strip()
            # Headings are short and don't end with a sentence terminator.
            if len(title) <= 60 and not title.endswith((".", "!", "?")):
                return level, m.group(1), title
            return None
    return None


def leading_prefix(line: str) -> str | None:
    """Return the numeric prefix of a numbered paragraph, e.g. '1.2.1'."""
    m = H4_RE.match(line) or H3_RE.match(line) or H2_RE.match(line) or H1_RE.match(line)
    if m:
        return m.group(1)
    return None


def render_cover(lines: list[str]) -> str:
    """Produce a tidy intro block from the cover page text.

    The cover is a mix of centered title lines and left-aligned intro
    paragraphs. Layout mode sometimes splits text mid-fragment (e.g.
    '©Disney/Pixar' becomes '©Disney' + '/Pixar' on separate visual lines),
    so we aggressively filter footer debris and then parse the joined body.
    """
    # Drop any line that looks like a footer fragment: standalone
    # copyright bits, page numbers, or trailing fragments.
    cleaned: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            continue
        if stripped in {"/Pixar", "and", "and 1", "and 2", "and 3"}:
            continue
        if re.fullmatch(r"\d{1,3}", stripped):
            continue
        if "disneylorcana.com" in stripped:
            continue
        if stripped.startswith("©"):
            continue
        if "Winnie the Pooh" in stripped or "Shepard" in stripped:
            continue
        cleaned.append(stripped)

    body = " ".join(cleaned)
    body = re.sub(r"\s+", " ", body).strip()

    pieces: list[str] = []

    # Title + version + effective date.
    title_match = re.search(
        r"COMPREHENSIVE RULES\s*Version\s*([\d.]+)\s*Effective\s+"
        r"([A-Za-z]+\s+\d{1,2},\s*\d{4})",
        body,
    )
    if title_match:
        version = title_match.group(1).strip()
        effective = title_match.group(2).strip()
        pieces.append(
            f"**Disney Lorcana Comprehensive Rules** — Version {version} "
            f"(Effective {effective})"
        )
        pieces.append("")

    # Note for new players.
    notes_match = re.search(
        r"A Note for New Players\s+(.+?)(?=INTRODUCTION|$)", body
    )
    if notes_match:
        notes_text = notes_match.group(1).strip()
        pieces.append("## A Note for New Players")
        pieces.append("")
        pieces.append(notes_text)
        pieces.append("")

    # Introduction.
    intro_match = re.search(r"INTRODUCTION\s+(.+)$", body)
    if intro_match:
        intro_text = intro_match.group(1).strip()
        pieces.append("## Introduction")
        pieces.append("")
        pieces.append(intro_text)
        pieces.append("")

    return "\n".join(p for p in pieces if p is not None).strip("\n")


def normalize_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def looks_like_contents_page(lines: list[str]) -> bool:
    """The contents page is laid out in two columns: many short lines whose
    concatenation produces the full TOC. We detect it by the presence of
    the literal 'CONTENTS' heading and lots of short numbered lines."""
    has_contents = any(l.strip() == "CONTENTS" for l in lines[:20])
    if not has_contents:
        return False
    short_count = sum(1 for l in lines if l.strip() and len(l.strip()) < 40)
    return short_count >= 10


def page_to_markdown(page_text: str) -> str:
    raw_lines = page_text.splitlines()
    # Drop lines that *are* footer fragments before any further processing.
    # The PDF sometimes splits "©Disney/Pixar" into "©Disney" on one row and
    # "/Pixar" on the next visual row, so we drop both halves explicitly.
    raw_lines = [
        ln for ln in raw_lines
        if ln.strip() not in {
            "/Pixar",
            "©Disney",
            "©Disney/Pixar",
            "disneylorcana.com",
        }
        and "Winnie the Pooh" not in ln
        and "E.H. Shepard" not in ln
        and "E. H. Shepard" not in ln
    ]
    lines = [strip_footer(ln) for ln in raw_lines]
    # Drop lines that became empty after footer stripping.
    lines = [ln for ln in lines if ln.strip()]

    # Cover page: contains the centered "COMPREHENSIVE RULES" title plus the
    # new-player note. Render it as a clean intro block.
    if any("COMPREHENSIVE RULES" in ln for ln in lines[:5]):
        return render_cover(lines)

    if looks_like_contents_page(lines):
        # Replace with a single placeholder; we'll skip it.
        return ""

    # Determine the minimum indent per heading level. The PDF indents each
    # level a bit deeper than the previous one, but indents aren't stable
    # across pages, so we use the level-by-level minimum on this page to
    # decide what counts as a heading vs a body paragraph at that depth.
    min_indent_per_level: dict[int, int] = {}
    for ln in lines:
        h = classify_heading(ln)
        if h is None:
            continue
        level = h[0]
        indent = normalize_indent(ln)
        cur = min_indent_per_level.get(level)
        if cur is None or indent < cur:
            min_indent_per_level[level] = indent

    out: list[str] = []
    current_paragraph: list[str] = []
    current_prefix: str | None = None

    def flush_paragraph() -> None:
        nonlocal current_paragraph, current_prefix
        if not current_paragraph:
            return
        joined = " ".join(current_paragraph)
        joined = re.sub(r"\s+", " ", joined).strip()
        if joined:
            out.append(joined)
        current_paragraph = []
        current_prefix = None

    for line in lines:
        if not line.strip():
            flush_paragraph()
            out.append("")
            continue

        indent = normalize_indent(line)
        content = line.strip()

        heading = classify_heading(line)
        if heading is not None:
            level, number, title = heading
            min_indent = min_indent_per_level.get(level)
            if min_indent is not None and indent == min_indent:
                flush_paragraph()
                out.append("")
                out.append(f"{'#' * level} {number} {title}")
                out.append("")
                continue

        prefix = leading_prefix(line)

        # Numbered line at a deeper indent than headings: start of a body
        # paragraph for that rule.
        if prefix is not None:
            if prefix != current_prefix:
                flush_paragraph()
                current_prefix = prefix
            current_paragraph.append(content)
            continue

        # Continuation line: append to current paragraph.
        if current_prefix is not None:
            current_paragraph.append(content)
            continue

        # Anything else (free text): start its own block.
        flush_paragraph()
        current_paragraph.append(content)

    flush_paragraph()

    # Collapse runs of blank lines to a single blank.
    cleaned: list[str] = []
    prev_blank = False
    for ln in out:
        is_blank = not ln.strip()
        if is_blank and prev_blank:
            continue
        cleaned.append(ln)
        prev_blank = is_blank
    return "\n".join(cleaned).strip("\n")


def pdf_to_markdown(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    page_chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout") or ""
        md = page_to_markdown(text)
        if md:
            page_chunks.append(md)
    return "\n\n".join(page_chunks) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pdf",
        nargs="?",
        default="data/rules/comprehensive-rules-2.2.0-en.pdf",
        type=Path,
        help="Path to the Comprehensive Rules PDF.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output markdown path. Defaults to <pdf-stem>.md next to the PDF.",
    )
    args = parser.parse_args(argv)

    pdf_path: Path = args.pdf
    if not pdf_path.is_file():
        print(f"error: {pdf_path} not found", file=sys.stderr)
        return 1

    out_path: Path = args.output or pdf_path.with_suffix(".md")

    markdown = pdf_to_markdown(pdf_path)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"wrote {out_path} ({len(markdown):,} chars, {markdown.count(chr(10)):,} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
