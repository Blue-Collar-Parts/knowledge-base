"""Data figures and page images.

A data figure is a picture of the page's own data with its text twin: an image
file in `content/figures/` and the markdown table directly under the tag that
states everything the picture shows. Readers and machines that cannot see the
picture read the table, so a figure without its twin is rejected.

A page image is the `image` front matter of an article: one to three PNG files
in `content/figures/`, one per aspect ratio (16:9, 4:3, 1:1), the 16:9 file
first.

Every image file declares its provenance as an IPTC DigitalSourceType in its
XMP packet: a chart drawn from data is `dataDrivenMedia`, a generated image
`trainedAlgorithmicMedia`. A file with no declaration is rejected.

The rules here are kept in step with the website's knowledge-base loader, so a
page the website would refuse fails here first.
"""
from __future__ import annotations

import datetime
import re
import struct
from pathlib import Path

FIGURE_DIR = "figures"

# Matched with fullmatch, so a trailing newline is not accepted.
_KEBAB = r"[a-z0-9]+(?:-[a-z0-9]+)*"
FIGURE_FILE_RE = re.compile(rf"{FIGURE_DIR}/({_KEBAB}\.(?:png|svg))")
PAGE_IMAGE_FILE_RE = re.compile(rf"{FIGURE_DIR}/({_KEBAB}\.png)")
FIGURE_NAME_RE = re.compile(rf"{_KEBAB}\.(?:png|svg)")
FIGURE_ID_RE = re.compile(_KEBAB)
ISO_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# A decimal number as JavaScript's Number() reads one; float() alone would also take "inf" and "1_000".
_DECIMAL_RE = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")

# The IPTC Digital Source Type vocabulary (cv.iptc.org/newscodes/digitalsourcetype).
IPTC_DIGITAL_SOURCE_TYPES = (
    "digitalCapture",
    "negativeFilm",
    "positiveFilm",
    "print",
    "minorHumanEdits",
    "compositeCapture",
    "algorithmicallyEnhanced",
    "dataDrivenMedia",
    "digitalArt",
    "virtualRecording",
    "compositeSynthetic",
    "trainedAlgorithmicMedia",
    "compositeWithTrainedAlgorithmicMedia",
    "algorithmicMedia",
    "screenCapture",
)
# Attribute (`DigitalSourceType="…"`), element text, `rdf:li`, or
# `rdf:resource="…"`: the forms XMP writers emit.
DIGITAL_SOURCE_TYPE_RE = re.compile(
    r"""DigitalSourceType(?:\s*=\s*["']|>\s*(?:<rdf:li[^>]*>)?|\s+rdf:resource\s*=\s*["'])\s*"""
    r"https?://cv\.iptc\.org/newscodes/digitalsourcetype/([A-Za-z]+)"
)

ATTRIBUTES = ("src", "alt", "caption", "source", "asOf", "table", "tableCaption")
MAX_TABLE_COLUMNS = 8

# Block only, alone on its line, self-closing: a figure inside a paragraph or a
# heading is invalid HTML.
TAG_RE = re.compile(r'^<KbDataFigure((?:[ \t]+[A-Za-z]+="[^"\n`]*")*)[ \t]*/>[ \t]*$', re.MULTILINE)
_ATTRIBUTE_RE = re.compile(r'[ \t]+([A-Za-z]+)="([^"\n`]*)"')
_FENCE_RE = re.compile(r"^(```|~~~)[^\n]*\n[\s\S]*?^\1[ \t]*$", re.MULTILINE)
_DELIMITER_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)*\s*:?-+:?\s*\|?\s*$")
_H2_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
_SVG_ACTIVE_RE = re.compile(
    r"""<script\b|<foreignObject\b|<[^>]*\son[a-z]+\s*=|(?:xlink:)?href\s*=\s*["'](?!#)|url\(\s*["']?(?!#)|@import|javascript:|<!ENTITY""",
    re.IGNORECASE,
)

PAGE_IMAGE_MIN_PIXELS = 50_000
PAGE_IMAGE_RATIOS = {"16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1.0}

TAG_HINT = '<KbDataFigure … /> on its own line above its table'


class FigureError(ValueError):
    pass


def mask_fenced_code(markdown: str) -> str:
    """Fenced code blanked character for character, so tags in it are ignored and lines hold."""
    return _FENCE_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), markdown)


def heading_id(text: str) -> str:
    """A heading's fragment id, as the website derives it."""
    text = re.sub(r"[’']", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


# --- image files ------------------------------------------------------------


def _number(value: str) -> float | None:
    """A decimal number, or None where JavaScript's Number() gives NaN ('' counts as 0, as there)."""
    value = value.strip()
    if not value:
        return 0.0
    return float(value) if _DECIMAL_RE.fullmatch(value) else None


def _svg_length(value: str | None) -> float:
    """A width or height; missing or unparsable is 0, so the viewBox is used."""
    if value is None:
        return 0.0
    return _number(re.sub(r"px\Z", "", value)) or 0.0


def read_image_size(data: bytes, name: str) -> tuple[float, float]:
    """Width and height from the PNG IHDR, or the SVG root's width/height or viewBox."""
    if name.endswith(".png"):
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise FigureError(f"{name} is not a PNG file")
        width, height = struct.unpack(">II", data[16:24])
        return float(width), float(height)
    root = re.search(r"<svg\b[^>]*>", data.decode("utf-8", errors="replace"))
    if not root:
        raise FigureError(f"{name} is not an SVG file")

    def attr(attr_name: str) -> str | None:
        found = re.search(rf'\s{attr_name}="([^"]*)"', root.group(0))
        return found.group(1) if found else None

    width, height = _svg_length(attr("width")), _svg_length(attr("height"))
    if width > 0 and height > 0:
        return width, height
    box_attr = attr("viewBox")
    if box_attr is not None:
        box = [_number(n) for n in re.split(r"[\s,]+", box_attr.strip())]
        if len(box) == 4 and box[2] and box[3] and box[2] > 0 and box[3] > 0:
            return box[2], box[3]
    raise FigureError(f"{name} must give its size: width and height, or a viewBox")


def read_digital_source_type(data: bytes, name: str) -> str:
    """The IPTC DigitalSourceType the file's XMP declares (uncompressed, so it is readable)."""
    found = DIGITAL_SOURCE_TYPE_RE.search(data.decode("latin-1"))
    if not found:
        raise FigureError(
            f"{name} declares no IPTC DigitalSourceType in its XMP; a chart drawn from data "
            "is dataDrivenMedia, a generated image trainedAlgorithmicMedia"
        )
    code = found.group(1)
    if code not in IPTC_DIGITAL_SOURCE_TYPES:
        raise FigureError(f'{name} declares DigitalSourceType "{code}", which is not an IPTC code')
    return code


def check_svg_is_inert(svg: str, name: str) -> None:
    """A figure is a drawing: no script, event handler, embedded HTML or reference to another file."""
    active = _SVG_ACTIVE_RE.search(svg)
    if active:
        raise FigureError(f'{name} must be a plain drawing; it contains "{active.group(0).strip()}"')


def check_image_bytes(data: bytes, name: str) -> tuple[float, float]:
    """Every check on an image file's contents; returns its size."""
    if name.endswith(".svg"):
        check_svg_is_inert(data.decode("utf-8", errors="replace"), name)
    size = read_image_size(data, name)
    read_digital_source_type(data, name)
    return size


def _read_image_file(
    content_dir: Path, file: object, pattern: re.Pattern[str], formats: str, what: str
) -> tuple[float, float]:
    if not isinstance(file, str) or not pattern.fullmatch(file):
        raise FigureError(
            f'{what} "{file}" must name a file in the {FIGURE_DIR}/ directory ({formats}, '
            'kebab-case name); remote URLs and ".." paths are not accepted'
        )
    full = content_dir / file
    if not full.is_file():
        raise FigureError(f'{what} "{file}" does not exist (expected content/{file})')
    return check_image_bytes(full.read_bytes(), file)


def read_figure_file(content_dir: Path, file: object) -> tuple[float, float]:
    return _read_image_file(content_dir, file, FIGURE_FILE_RE, "PNG or SVG", "<KbDataFigure> src")


def check_figure_directory(content_dir: Path) -> list[str]:
    """Every file in content/figures/ is a kebab-case PNG or SVG that passes the file checks."""
    directory = content_dir / FIGURE_DIR
    if not directory.exists():
        return []
    errs: list[str] = []
    for path in sorted(directory.rglob("*")):
        if any(part.startswith(".") for part in path.relative_to(directory).parts):
            continue  # editor and OS files (.DS_Store), never published
        rel = path.relative_to(content_dir).as_posix()
        if path.is_dir():
            errs.append(f"{rel}: {FIGURE_DIR}/ holds image files only, no subdirectories")
            continue
        if path.parent != directory or not FIGURE_NAME_RE.fullmatch(path.name):
            errs.append(f"{rel}: a figure file is a kebab-case .png or .svg name in {FIGURE_DIR}/")
            continue
        try:
            check_image_bytes(path.read_bytes(), rel)
        except FigureError as exc:
            errs.append(str(exc))
    return errs


# --- page images (front matter `image`) ----------------------------------------


def _aspect_ratio(width: float, height: float) -> str | None:
    for ratio, value in PAGE_IMAGE_RATIOS.items():
        if abs(width / height - value) < 0.02:
            return ratio
    return None


def check_page_images(meta: dict, content_dir: Path) -> list[str]:
    """`image`: one to three PNGs in figures/, articles only, one per ratio, the 16:9 first."""
    if "image" not in meta:
        return []
    files = meta["image"]
    if not (isinstance(files, list) and all(isinstance(f, str) and f.strip() for f in files)):
        return ["`image` must be an array of file paths"]
    if not 1 <= len(files) <= 3:
        return ["`image` must list one to three files, one per aspect ratio (16:9, 4:3, 1:1)"]
    if meta.get("kind") != "article":
        return ["`image` is for articles; FAQ pages take no image"]
    if len(set(files)) != len(files):
        return ["`image` lists a file twice"]
    ratios: set[str] = set()
    for index, file in enumerate(files):
        try:
            width, height = _read_image_file(content_dir, file, PAGE_IMAGE_FILE_RE, "PNG", "image")
        except FigureError as exc:
            return [str(exc)]
        size = f"{width:g}×{height:g}"
        if width * height < PAGE_IMAGE_MIN_PIXELS:
            return [f'image "{file}" is {size}; a page image has at least {PAGE_IMAGE_MIN_PIXELS} pixels']
        ratio = _aspect_ratio(width, height)
        if ratio is None:
            return [f'image "{file}" is {size}; a page image is 16:9, 4:3 or 1:1']
        if index == 0 and ratio != "16:9":
            return [f'image "{file}" is {ratio}; the first page image is the 16:9 share image']
        if ratio in ratios:
            return [f"`image` lists two {ratio} files; give one per aspect ratio"]
        ratios.add(ratio)
    return []


# --- the tag and its twin -----------------------------------------------------


def _is_real_date(value: str) -> bool:
    if not ISO_DATE_RE.fullmatch(value):
        return False
    try:
        return datetime.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def parse_attributes(attributes: str) -> dict[str, str]:
    """One tag's attributes; rejects an unknown, repeated, missing or malformed one."""
    seen: dict[str, str] = {}

    def take(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        if name not in ATTRIBUTES:
            raise FigureError(
                f'<KbDataFigure {name}="…"> is not an attribute; the attributes are {", ".join(ATTRIBUTES)}'
            )
        if name in seen:
            raise FigureError(f"<KbDataFigure> gives {name} twice")
        seen[name] = value
        return ""

    leftover = _ATTRIBUTE_RE.sub(take, attributes)
    if leftover.strip():
        raise FigureError(
            f"<KbDataFigure> has a malformed attribute: {leftover.strip()} "
            '(each is name="value"; a value cannot contain a double quote)'
        )
    for name in ATTRIBUTES:
        if not seen.get(name, "").strip():
            raise FigureError(f"<KbDataFigure> needs a non-empty {name}")
    # The alt states the finding and ends by naming the twin table.
    last_sentence = re.split(r"(?<=[.;])\s+", seen["alt"].strip())[-1]
    if not re.search(r"\btable\b", last_sentence, re.IGNORECASE):
        raise FigureError(
            '<KbDataFigure alt="…"> must end by naming the table under the figure '
            '("… the table below gives each band.")'
        )
    as_of = seen["asOf"]
    if not _is_real_date(as_of):
        raise FigureError(f'<KbDataFigure asOf="{as_of}"> must be a real date, YYYY-MM-DD')
    if not FIGURE_ID_RE.fullmatch(seen["table"]):
        raise FigureError(f'<KbDataFigure table="{seen["table"]}"> must be a kebab-case id')
    return seen


def _table_cells(row: str) -> list[str]:
    """A row's cells: escaped pipes and pipes in code spans are cell text, not separators."""
    masked = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), row.replace("\\|", "  "))
    return masked.strip().removeprefix("|").removesuffix("|").split("|")


def _table_columns(lines: list[str], start: int) -> int | None:
    """The column count when lines[start] opens a GFM table (a pipe row, then a matching delimiter row)."""
    header = lines[start] if start < len(lines) else ""
    delimiter = lines[start + 1] if start + 1 < len(lines) else ""
    if "|" not in header or not _DELIMITER_RE.match(delimiter):
        return None
    columns = len(_table_cells(header))
    return columns if columns == len(_table_cells(delimiter)) else None


def check_data_figures(body: str, content_dir: Path) -> list[str]:
    """Each figure's grammar, file and twin table, and the twin ids' uniqueness on the page."""
    text = mask_fenced_code(body)
    lines = text.split("\n")
    for line in lines:
        if "<KbDataFigure" in line and not TAG_RE.fullmatch(line):
            return [
                f"{line.strip()[:60]}… must stand alone on one line, as name=\"value\" attributes "
                'ending " />", with no backtick, directly above its table; show the tag as an '
                "example only in a fenced code block"
            ]
    tables: list[str] = []
    for match in TAG_RE.finditer(text):
        try:
            tag = parse_attributes(match.group(1))
            read_figure_file(content_dir, tag["src"])
        except FigureError as exc:
            return [str(exc)]
        table = tag["table"]
        nxt = text[: match.start()].count("\n") + 1
        while nxt < len(lines) and lines[nxt].strip() == "":
            nxt += 1
        columns = _table_columns(lines, nxt)
        if columns is None:
            return [
                f'<KbDataFigure table="{table}"> has no twin table: the next block after the figure '
                "must be the markdown table of its data (a header row, then a delimiter row with as many cells)"
            ]
        if columns > MAX_TABLE_COLUMNS:
            return [
                f"<KbDataFigure table=\"{table}\">'s table has {columns} columns; "
                f"a twin table has at most {MAX_TABLE_COLUMNS}"
            ]
        tables.append(table)
    # Each twin id is a DOM id, and its caption takes `<id>-caption`: neither may
    # repeat another figure's id or an H2's fragment id.
    headings = {heading_id(re.sub(r"[*_`]", "", m.group(1))) for m in _H2_RE.finditer(text)}
    used: set[str] = set()
    for table in tables:
        if table in used:
            return [f'<KbDataFigure table="{table}"> is used twice; each figure has its own twin table']
        if table in headings or f"{table}-caption" in headings:
            return [f'<KbDataFigure table="{table}"> repeats a heading\'s id on this page; choose another id']
        used.add(table)
    return []
