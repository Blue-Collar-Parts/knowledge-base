import struct
import sys
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kb_figures as f  # noqa: E402
import validate_content as v  # noqa: E402

from test_validate_content import FRONT, has, meta, write  # noqa: E402

SLUGS = {"alpha", "beta", "other-page"}
IPTC = "http://cv.iptc.org/newscodes/digitalsourcetype/"


def xmp(code="dataDrivenMedia"):
    return (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description '
        f'Iptc4xmpExt:DigitalSourceType="{IPTC}{code}"/></rdf:RDF></x:xmpmeta>'
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(width=320, height=180, code="dataDrivenMedia"):
    """A PNG header with an uncompressed iTXt XMP chunk; enough for the size and provenance reads."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    out = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
    if code is not None:
        out += _chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + xmp(code).encode())
    return out + _chunk(b"IEND", b"")


def svg(extra="", size='width="640" height="360"', code="dataDrivenMedia"):
    meta_block = f"<metadata>{xmp(code)}</metadata>" if code else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" {size}>{meta_block}'
        f'<rect width="10" height="10"/>{extra}</svg>'
    ).encode()


@pytest.fixture
def content(tmp_path):
    root = tmp_path / "content"
    (root / "figures").mkdir(parents=True)
    (root / "figures" / "cited-systems.png").write_bytes(png())
    (root / "figures" / "cited-systems.svg").write_bytes(svg())
    return root


def tag(**over):
    attrs = {
        "src": "figures/cited-systems.png",
        "alt": "Brakes lead the cited systems. The table below gives each system.",
        "caption": "Brakes are the most cited system",
        "source": "FMCSA vehicle inspection data",
        "asOf": "2026-09-27",
        "table": "cited-systems",
        "tableCaption": "Cited units by system",
    }
    attrs.update(over)
    return "<KbDataFigure " + " ".join(f'{k}="{val}"' for k, val in attrs.items() if val is not None) + " />"


TABLE = "| System | Share |\n| --- | ---: |\n| Brakes | 30% |\n| Lighting | 25% |\n"


def page(figure=None, table=TABLE, before="Intro.\n\n"):
    return f"{before}{figure or tag()}\n\n{table}\nAfter.\n"


def check(content, body, m=None):
    return v.validate_page(m or meta(), body, "product", "alpha", SLUGS, content)


# --- a valid figure --------------------------------------------------------


def test_figure_with_twin_table_passes(content):
    assert check(content, page()) == []


def test_svg_figure_passes(content):
    assert check(content, page(tag(src="figures/cited-systems.svg"))) == []


def test_figure_directly_above_table_passes(content):
    assert check(content, f"{tag()}\n{TABLE}") == []


def test_two_figures_with_their_own_tables_pass(content):
    second = tag(table="cited-ages", alt="Older units lead. The table below gives each band.")
    assert check(content, page() + "\n" + page(second)) == []


def test_tag_in_a_tilde_fence_is_ignored(content):
    assert check(content, "~~~\n<KbDataFigure />\n~~~\n") == []


def test_fenced_heading_does_not_collide(content):
    assert check(content, page(before="```md\n## Cited systems\n```\n\n")) == []


def test_alt_sentences_split_on_semicolons(content):
    assert check(content, page(tag(alt="Brakes lead; the table below gives each system."))) == []
    assert has(check(content, page(tag(alt="The table below gives each; brakes lead."))), "must end by naming the table")


def test_tag_in_a_fence_is_ignored(content):
    body = "Example:\n\n```mdx\n<KbDataFigure src=\"https://x\" />\n```\n\nText.\n"
    assert check(content, body) == []


def test_figure_is_a_listed_component(content):
    errs = check(content, "<Capture />")
    assert has(errs, "<KbDataFigure … /> on its own line above its table")


# --- attributes ------------------------------------------------------------


def test_unknown_attribute_is_rejected(content):
    body = page(tag().replace(" />", ' width="400" />'))
    assert has(check(content, body), '<KbDataFigure width="…"> is not an attribute')


def test_repeated_attribute_is_rejected(content):
    body = page(tag().replace(" />", ' table="other" />'))
    assert has(check(content, body), "gives table twice")


@pytest.mark.parametrize("name", f.ATTRIBUTES)
def test_missing_attribute_is_rejected(content, name):
    assert has(check(content, page(tag(**{name: None}))), f"needs a non-empty {name}")


def test_empty_attribute_is_rejected(content):
    assert has(check(content, page(tag(caption=" "))), "needs a non-empty caption")


def test_bare_attribute_makes_the_line_loose(content):
    body = page(tag().replace(" />", " hidden />"))
    assert has(check(content, body), "must stand alone on one line")


def test_alt_must_end_by_naming_the_table(content):
    errs = check(content, page(tag(alt="The table below gives each system. Brakes lead.")))
    assert has(errs, "must end by naming the table")


@pytest.mark.parametrize("as_of", ["2026-02-30", "2026-13-01", "27 Sep 2026", "2026-9-27"])
def test_as_of_must_be_a_real_date(content, as_of):
    assert has(check(content, page(tag(asOf=as_of))), "must be a real date")


@pytest.mark.parametrize("table", ["Cited_Systems", "cited systems", "-cited"])
def test_table_id_must_be_kebab_case(content, table):
    assert has(check(content, page(tag(table=table))), "must be a kebab-case id")


# --- the twin table ----------------------------------------------------------


def test_missing_twin_table_is_rejected(content):
    assert has(check(content, f"{tag()}\n\nJust prose.\n"), "has no twin table")


def test_figure_at_end_of_page_is_rejected(content):
    assert has(check(content, f"Intro.\n\n{tag()}\n"), "has no twin table")


def test_header_and_delimiter_cell_counts_must_match(content):
    table = "| System | Share |\n| --- | --- | --- |\n| Brakes | 30% |\n"
    assert has(check(content, page(table=table)), "has no twin table")


def test_escaped_pipe_is_cell_text(content):
    table = "| System \\| part | Share |\n| --- | --- |\n| Brakes | 30% |\n"
    assert check(content, page(table=table)) == []


def test_eight_columns_pass_and_nine_are_rejected(content):
    def wide(n):
        return "|" + "|".join(f" c{i} " for i in range(n)) + "|\n|" + "|".join([" --- "] * n) + "|\n"

    assert check(content, page(table=wide(8))) == []
    assert has(check(content, page(table=wide(9))), "has 9 columns; a twin table has at most 8")


def test_table_id_used_twice_is_rejected(content):
    assert has(check(content, page() + "\n" + page()), "is used twice")


@pytest.mark.parametrize("heading", ["## Cited systems", "## *Cited* `systems`", "## Cited systems caption"])
def test_table_id_must_not_repeat_a_heading_id(content, heading):
    assert has(check(content, page(before=f"{heading}\n\n")), "repeats a heading's id")


def test_h3_does_not_collide(content):
    assert check(content, page(before="### Cited systems\n\n")) == []


# --- placement ---------------------------------------------------------------


@pytest.mark.parametrize("body", [
    f"## {tag()}\n\n{TABLE}",
    f"See {tag()} here.\n\n{TABLE}",
    f"  {tag()}\n\n{TABLE}",
    f"`{tag()}`\n\n{TABLE}",
    tag().replace(" />", "></KbDataFigure>") + f"\n\n{TABLE}",
])
def test_figure_not_alone_on_its_line_is_rejected(content, body):
    assert has(check(content, body), "must stand alone on one line")


def test_self_closing_without_space_passes(content):
    # The website's grammar allows `"/>`, so the validator does too.
    assert check(content, page(tag().replace(" />", "/>"))) == []


def test_figure_in_qa_is_rejected(content):
    m = meta(kind="faq", qa=[{"question": "Q?", "answer": tag()}])
    assert has(check(content, "Text.", m), "must not contain components")


# --- src and the file -------------------------------------------------------


@pytest.mark.parametrize("src", [
    "https://example.com/chart.png",
    "/kb/figures/cited-systems.png",
    "figures/../figures/cited-systems.png",
    "figures/cited-systems.jpg",
    "figures/Cited_Systems.png",
    "cited-systems.png",
])
def test_src_must_name_a_bundled_figure(content, src):
    assert has(check(content, page(tag(src=src))), "must name a file in the figures/ directory")


def test_src_file_must_exist(content):
    assert has(check(content, page(tag(src="figures/absent.png"))), "does not exist")


def test_file_without_provenance_is_rejected(content):
    (content / "figures" / "cited-systems.png").write_bytes(png(code=None))
    assert has(check(content, page()), "declares no IPTC DigitalSourceType")


def test_file_with_unknown_provenance_code_is_rejected(content):
    (content / "figures" / "cited-systems.png").write_bytes(png(code="madeUp"))
    assert has(check(content, page()), 'declares DigitalSourceType "madeUp"')


def test_provenance_as_element_text_is_read():
    data = f"<Iptc4xmpExt:DigitalSourceType>{IPTC}trainedAlgorithmicMedia</Iptc4xmpExt:DigitalSourceType>"
    assert f.read_digital_source_type(data.encode(), "x.svg") == "trainedAlgorithmicMedia"


def test_not_a_png_is_rejected(content):
    (content / "figures" / "cited-systems.png").write_bytes(b"GIF89a" + b"\x00" * 30)
    assert has(check(content, page()), "is not a PNG file")


@pytest.mark.parametrize("extra", [
    "<script>alert(1)</script>",
    '<rect onclick="x()"/>',
    "<foreignObject><div/></foreignObject>",
    '<image href="https://example.com/x.png"/>',
    '<use xlink:href="other.svg#a"/>',
    '<rect style="fill:url(https://example.com/p)"/>',
    "<style>@import 'x.css';</style>",
    '<a href="javascript:x()"/>',
])
def test_active_svg_is_rejected(content, extra):
    (content / "figures" / "cited-systems.svg").write_bytes(svg(extra))
    errs = check(content, page(tag(src="figures/cited-systems.svg")))
    assert has(errs, "must be a plain drawing")


def test_svg_entity_is_rejected(content):
    data = b'<!DOCTYPE svg [<!ENTITY a "b">]>' + svg()
    (content / "figures" / "cited-systems.svg").write_bytes(data)
    assert has(check(content, page(tag(src="figures/cited-systems.svg"))), "must be a plain drawing")


def test_svg_local_references_pass(content):
    extra = '<defs><linearGradient id="g"/></defs><rect fill="url(#g)"/><use href="#g"/>'
    (content / "figures" / "cited-systems.svg").write_bytes(svg(extra))
    assert check(content, page(tag(src="figures/cited-systems.svg"))) == []


@pytest.mark.parametrize("size", ['width="100%" height="100%" viewBox="0 0 640 360"', 'viewBox="0,0,640,360"'])
def test_svg_size_falls_back_to_view_box(size):
    assert f.read_image_size(svg(size=size), "x.svg") == (640.0, 360.0)


@pytest.mark.parametrize("size", ['width="inf" height="inf"', 'width="1_000" height="500"', 'viewBox="0 0 inf 360"'])
def test_svg_size_reads_numbers_as_the_website_does(size):
    with pytest.raises(f.FigureError, match="must give its size"):
        f.read_image_size(svg(size=size), "x.svg")


def test_trailing_newline_in_a_path_is_rejected(images):
    assert has(check(images, "Text.", meta(image=["figures/wide.png\n"])), "must name a file in the figures/ directory")


@pytest.mark.parametrize("size, expected", [
    ('width="1e2" height="50"', (100.0, 50.0)),
    ('width="100px" height=".5e2px"', (100.0, 50.0)),
    ('width="100px\n" height="50" viewBox="0 0 10 10"', (10.0, 10.0)),
])
def test_svg_size_parses_decimal_forms(size, expected):
    assert f.read_image_size(svg(size=size), "x.svg") == expected


def test_dotfiles_in_figures_are_skipped(content):
    (content / "figures" / ".DS_Store").write_bytes(b"\x00")
    assert v.validate_content(content) == []


def test_svg_without_a_size_is_rejected(content):
    (content / "figures" / "cited-systems.svg").write_bytes(svg(size=""))
    assert has(check(content, page(tag(src="figures/cited-systems.svg"))), "must give its size")


# --- page images (front matter `image`) -------------------------------------


@pytest.fixture
def images(content):
    for name, (w, h) in {"wide": (320, 180), "wide-4x3": (280, 210), "wide-1x1": (240, 240),
                         "four-three": (280, 210), "square": (240, 240),
                         "small": (160, 90), "tall": (180, 320)}.items():
        (content / "figures" / f"{name}.png").write_bytes(png(w, h))
    return content


# A page whose figure is the 16:9 share image `figures/wide.png`.
WIDE = page(tag(src="figures/wide.png"))


def test_page_images_pass(images):
    m = meta(image=["figures/wide.png", "figures/wide-4x3.png", "figures/wide-1x1.png"])
    assert check(images, WIDE, m) == []


def test_one_page_image_passes(images):
    assert check(images, WIDE, meta(image=["figures/wide.png"])) == []


def test_share_image_must_be_a_figure_on_the_page(images):
    assert has(check(images, "Text.", meta(image=["figures/wide.png"])), 'image "figures/wide.png" is not on the page')
    other = page(tag(src="figures/cited-systems.png"))
    assert has(check(images, other, meta(image=["figures/wide.png"])), "is not on the page")


def test_share_image_may_be_the_png_of_an_svg_figure(content):
    (content / "figures" / "cited-systems.png").write_bytes(png(320, 180))
    body = page(tag(src="figures/cited-systems.svg"))
    assert check(content, body, meta(image=["figures/cited-systems.png"])) == []


def test_a_figure_in_fenced_code_does_not_show_the_share_image(images):
    body = "```\n" + tag(src="figures/wide.png") + "\n```\n"
    assert has(check(images, body, meta(image=["figures/wide.png"])), "is not on the page")


@pytest.mark.parametrize("files, fragment", [
    (["figures/wide.png", "figures/square.png"],
     'image "figures/square.png" must be a crop of "figures/wide.png", named "figures/wide-1x1.png"'),
    (["figures/wide.png", "figures/four-three.png"], 'named "figures/wide-4x3.png"'),
    # The suffix is keyed to the crop's own ratio, not to its position.
    (["figures/wide.png", "figures/wide-4x3.png", "figures/four-three.png"], "two 4:3 files"),
])
def test_crops_are_named_after_the_share_image(images, files, fragment):
    assert has(check(images, WIDE, meta(image=files)), fragment)


def test_crop_name_must_match_its_ratio(images):
    (images / "figures" / "wide-1x1.png").write_bytes(png(280, 210))  # 4:3 under a 1:1 name
    assert has(check(images, WIDE, meta(image=["figures/wide.png", "figures/wide-1x1.png"])),
               'named "figures/wide-4x3.png"')


def test_a_shape_error_is_reported_before_the_page_check(images):
    errs = check(images, "Text.", meta(image=["figures/tall.png"]))
    assert has(errs, "16:9, 4:3 or 1:1")
    assert not has(errs, "is not on the page")


def test_readme_page_image_example_passes(content):
    """The README's `image` example, beside the figure it names."""
    for name, (w, h) in {"cited-systems": (1200, 675), "cited-systems-4x3": (1200, 900),
                         "cited-systems-1x1": (1200, 1200)}.items():
        (content / "figures" / f"{name}.png").write_bytes(png(w, h))
    m = meta(image=["figures/cited-systems.png", "figures/cited-systems-4x3.png", "figures/cited-systems-1x1.png"])
    assert check(content, page(tag(src="figures/cited-systems.svg")), m) == []


@pytest.mark.parametrize("files, fragment", [
    ([], "one to three files"),
    (["figures/wide.png", "figures/four-three.png", "figures/square.png", "figures/tall.png"], "one to three files"),
    ("figures/wide.png", "must be an array"),
    (["figures/wide.png", "figures/wide.png"], "lists a file twice"),
    (["figures/cited-systems.svg"], "must name a file in the figures/ directory (PNG"),
    (["https://example.com/wide.png"], "must name a file in the figures/ directory"),
    (["figures/absent.png"], "does not exist"),
    (["figures/small.png"], "at least 50000 pixels"),
    (["figures/tall.png"], "16:9, 4:3 or 1:1"),
    (["figures/square.png"], "the first page image is the 16:9 share image"),
    (["figures/wide.png", "figures/wide-two.png"], "two 16:9 files"),
])
def test_page_image_rules(images, files, fragment):
    (images / "figures" / "wide-two.png").write_bytes(png(640, 360))
    assert has(check(images, "Text.", meta(image=files)), fragment)


def test_page_image_is_for_articles_only(images):
    m = meta(kind="faq", qa=[{"question": "Q?", "answer": "A."}], image=["figures/wide.png"])
    assert has(check(images, "Text.", m), "`image` is for articles")


# --- slug and the figures directory -------------------------------------------


def test_figures_slug_is_reserved(content):
    errs = v.validate_page(meta(slug="figures"), "Text.", "product", "figures", SLUGS, content)
    assert has(errs, "slug `figures` is reserved")


def test_repo_walk_with_a_figure_passes(content):
    write(content / "product" / "alpha.mdx", FRONT.format(slug="alpha"), body=page())
    assert v.validate_content(content) == []


def test_repo_walk_reports_a_bad_figure_page(content):
    write(content / "product" / "alpha.mdx", FRONT.format(slug="alpha"), body=f"{tag()}\n\nNo table.\n")
    assert any("has no twin table" in e for e in v.validate_content(content))


@pytest.mark.parametrize("name, data, fragment", [
    ("Chart.png", png(), "kebab-case .png or .svg"),
    ("chart.jpg", b"x", "kebab-case .png or .svg"),
    ("unlabelled.png", png(code=None), "declares no IPTC DigitalSourceType"),
    ("active.svg", svg("<script/>"), "must be a plain drawing"),
])
def test_every_file_in_figures_is_checked(content, name, data, fragment):
    (content / "figures" / name).write_bytes(data)
    errs = v.validate_content(content)
    assert any(fragment in e and e.startswith("content/figures/") for e in errs), errs


def test_figures_subdirectory_is_rejected(content):
    (content / "figures" / "nested").mkdir()
    assert any("no subdirectories" in e for e in v.validate_content(content))
