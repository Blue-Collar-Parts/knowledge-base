import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_content as v  # noqa: E402

SLUGS = {"alpha", "beta", "other-page"}


def meta(**over):
    base = {
        "slug": "alpha",
        "title": "Alpha",
        "description": "A page.",
        "track": "product",
        "kind": "article",
        "order": 10,
        "isRegulatoryAdjacent": False,
        "publishedAt": "2026-01-01",
        "cfr": [],
    }
    base.update(over)
    return base


def check(m, body="Plain text.", track_dir="product", stem="alpha", slugs=SLUGS):
    return v.validate_page(m, body, track_dir, stem, slugs)


def has(errs, fragment):
    return any(fragment in e for e in errs)


def test_valid_page_passes():
    assert check(meta()) == []


@pytest.mark.parametrize("field", ["slug", "title", "description", "track", "kind",
                                    "order", "isRegulatoryAdjacent", "publishedAt", "cfr"])
def test_required_field_missing(field):
    m = meta()
    del m[field]
    assert has(check(m), f"missing required field `{field}`")


def test_slug_must_match_filename():
    assert has(check(meta(slug="beta")), "must match filename")


def test_track_must_match_directory():
    assert has(check(meta(), track_dir="regulatory"), "must match directory")


def test_business_track_is_known():
    assert not has(check(meta(track="business"), track_dir="business"), "`track` must be one of")
    assert has(check(meta(track="sales"), track_dir="sales"), "`track` must be one of")


def test_kind_order_dates_boolean():
    assert has(check(meta(kind="post")), "`kind`")
    assert has(check(meta(order="ten")), "`order`")
    assert has(check(meta(order=True)), "`order`")
    assert has(check(meta(publishedAt="01/02/2026")), "`publishedAt`")
    assert has(check(meta(updatedAt="2026-1-2")), "`updatedAt`")
    assert has(check(meta(isRegulatoryAdjacent="yes")), "`isRegulatoryAdjacent`")


def test_faq_needs_qa():
    assert has(check(meta(kind="faq")), "requires a non-empty `qa`")
    ok = meta(kind="faq", qa=[{"question": "Q?", "answer": "A."}])
    assert check(ok) == []


def test_related_must_resolve():
    assert has(check(meta(related=["missing"])), "does not resolve")
    assert check(meta(related=["beta"])) == []


def test_maintenance_rules():
    m = meta(track="maintenance", isRegulatoryAdjacent=True, cfr=["49 CFR 396.17"])
    errs = check(m, track_dir="maintenance")
    assert has(errs, "isRegulatoryAdjacent: false")
    assert has(errs, "cfr: []")


@pytest.mark.parametrize("cite", [
    "49 CFR 396.17", "49 CFR 396.17(c)(2)", "49 CFR 393.47(e)", "49 CFR Part 396 Appendix A",
])
def test_cfr_canonical_passes(cite):
    assert check(meta(cfr=[cite], isRegulatoryAdjacent=True)) == []


@pytest.mark.parametrize("cite", [
    "49 CFR Part 396, Appendix A", "49 CFR §396.17", "CFR 396.17", "49 CFR 396.17 (c)",
])
def test_cfr_noncanonical_fails(cite):
    assert has(check(meta(cfr=[cite])), "canonical form")


def test_topics_empty_or_absent_passes():
    assert check(meta()) == []
    assert check(meta(topics=[])) == []


def test_known_topics_pass():
    assert check(meta(topics=["brakes_air", "tires_wheels"])) == []


def test_unknown_topic_fails():
    assert has(check(meta(topics=["not_a_topic"])), "not in vocabulary")


def test_duplicate_topic_fails():
    assert has(check(meta(topics=["engine", "engine"])), "more than once")


def test_pm_topic_with_cfr_rejected():
    errs = check(meta(topics=["pm_truck_otr"], cfr=["49 CFR 396.17"]))
    assert has(errs, "`pm_*` topic")


def test_pm_topic_without_cfr_passes():
    assert check(meta(topics=["pm_truck_otr"])) == []


def test_vocabulary_file_is_well_formed():
    vocab = v.load_topic_vocabulary()
    assert len(vocab) == 15
    assert all(t == t.lower() and " " not in t for t in vocab)


def test_next_step_related():
    ok = meta(nextStep={"kind": "related", "target": "beta", "text": "See beta"})
    assert check(ok) == []
    assert has(check(meta(nextStep={"kind": "related", "target": "alpha", "text": "x"})), "own slug")
    assert has(check(meta(nextStep={"kind": "related", "target": "zzz", "text": "x"})), "does not resolve")
    assert has(check(meta(nextStep={"kind": "related", "target": "beta"})), "`nextStep.text` is required")


def test_next_step_start_target_shape():
    ok = meta(nextStep={"kind": "start", "target": "/start/pm-service", "text": "Send a PM record"})
    assert check(ok) == []
    assert check(meta(nextStep={"kind": "start", "target": "/start", "text": "Get started"})) == []
    for bad in ("/start/PM", "start/pm", "/start/pm/x", "https://example.com/start", "/start/"):
        errs = check(meta(nextStep={"kind": "start", "target": bad, "text": "Go"}))
        assert has(errs, "`/start/<lowercase-kebab>`"), bad


def test_next_step_none_omits_target_and_text():
    assert check(meta(nextStep={"kind": "none"})) == []
    assert has(check(meta(nextStep={"kind": "none", "target": "beta"})), "omit `target`")


def test_next_step_text_rules():
    for text in ("Build your record.", "build your record", "BUILD YOUR RECORD!"):
        errs = check(meta(nextStep={"kind": "related", "target": "beta", "text": text}))
        assert has(errs, "Build your record"), text
    errs = check(meta(nextStep={"kind": "start", "target": "/start", "text": "A record that satisfies 396.17(c)"}))
    assert has(errs, "must not claim compliance")


def test_bad_next_step_kind():
    assert has(check(meta(nextStep={"kind": "cta"})), "`nextStep.kind`")


def test_internal_links_resolve():
    assert check(meta(), body="See [beta](/kb/beta) and [o](other-page).") == []
    assert has(check(meta(), body="See [x](/kb/nope)."), "`nope`")
    assert has(check(meta(), body="See [x](nope)."), "`nope`")
    assert check(meta(), body="See [x](/kb/beta#part) and [e](https://example.com/a).") == []
    assert check(meta(), body="```\n[x](/kb/nope)\n```\n") == []


# One failing and one passing case per private-data class, with fake numbers.
PRIVATE_CASES = [
    ("search volume", "The term has a search volume of 9,999 a month.", "The term has a clear search intent."),
    ("keyword difficulty", "Its keyword difficulty is 77.", "Its keyword choice is plain."),
    ("cost per click", "The CPC is $8.88 here.", "The page explains the work."),
    ("impressions", "It earned 12345 impressions last week.", "Impressions are not discussed here."),
    ("clicks", "That link drew 4,321 clicks.", "The link opens the page."),
    ("sessions", "There were 5,555 sessions in the month.", "A service session ends with a report."),
    ("visitors", "The page had 6,000 visitors.", "The page helps visitors find the record."),
    ("signups", "We saw 321 signups.", "Signups are not covered here."),
    ("conversion rate", "The conversion rate is 3.3%.", "A conversion is not described here."),
    ("score", "Its opportunity score is 88.", "The page has no scoring."),
    ("technician share", "The technician share is 44%.", "A technician writes the record."),
    ("business", "Blue Collar Parts has 777 customers.", "Blue Collar Parts sends the report to your customer."),
]


@pytest.mark.parametrize("name,bad,good", PRIVATE_CASES)
def test_private_number_scan(name, bad, good):
    assert v.scan_private_numbers(bad), name
    assert v.scan_private_numbers(good) == [], name


def test_scan_ignores_ordinary_numbers_and_urls():
    text = ("Torque is 150 ft-lb at 90 PSI within 14 months under 49 CFR 396.17. "
            "See [x](/kb/page-2024) and https://example.com/a/9999/clicks.")
    assert v.scan_private_numbers(text) == []


def test_scan_requires_same_sentence():
    assert v.scan_private_numbers("Clicks are not covered. There are 12 axles.") == []


def test_public_fmcsa_mix_with_method_passes():
    text = ("FMCSA vehicle inspection data, inspections from 2020-01-01 to 2020-12-31, "
            "one current version per inspection; mix among cited units. "
            "Of units cited for a vehicle violation, 11% were cited for lighting.")
    assert v.scan_private_numbers(text) == []


def test_scan_runs_on_page_text_and_qa():
    m = meta(description="It has 5,000 monthly searches.")
    assert has(check(m), "search volume")
    q = meta(kind="faq", qa=[{"question": "Q?", "answer": "A conversion rate of 4%."}])
    assert has(check(q), "conversion rate")


def write(path: Path, front: str, body="Body.\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + textwrap.dedent(front).strip() + "\n---\n" + body, encoding="utf-8")


FRONT = """
slug: {slug}
title: T
description: D
track: product
kind: article
order: 10
isRegulatoryAdjacent: false
publishedAt: 2026-01-01
cfr: []
nextStep:
  kind: start
  target: /start
  text: Get started
"""

STEP_BLOCK = "nextStep:\n  kind: start\n  target: /start\n  text: Get started\n"
FRONT_NO_STEP = FRONT.format(slug="alpha").replace(STEP_BLOCK, "")


def test_repo_walk_duplicate_slug_across_tracks(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", FRONT.format(slug="alpha"))
    write(content / "regulatory" / "alpha.mdx",
          FRONT.format(slug="alpha").replace("track: product", "track: regulatory"))
    assert any("already used" in e for e in v.validate_content(content))


def test_repo_walk_clean_and_dates_stay_strings(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", FRONT.format(slug="alpha"))
    assert v.validate_content(content) == []


def test_missing_front_matter(tmp_path):
    content = tmp_path / "content"
    (content / "product").mkdir(parents=True)
    (content / "product" / "alpha.mdx").write_text("no front matter", encoding="utf-8")
    assert any("front matter" in e for e in v.validate_content(content))


@pytest.mark.parametrize("tone", v.STATUS_TONES)
def test_status_component_passes(tone):
    assert check(meta(), body=f'A point reads <Status tone="{tone}">Words</Status>.') == []


def test_status_in_a_table_passes():
    body = '| Mark | Meaning |\n| --- | --- |\n| <Status tone="danger">Defect recorded</Status> | x |'
    assert check(meta(), body=body) == []


@pytest.mark.parametrize("body, fragment", [
    ('<Status tone="orange">Send</Status>', "must be one of"),
    ("<Button>Send</Button>", "not a knowledge-base component"),
    ("<Status>Passed</Status>", "not a knowledge-base component"),
    ("<Status tone={x}>Passed</Status>", "not a knowledge-base component"),
    ('## Why <Status tone="success">Passed</Status>', "not allowed in a heading"),
])
def test_status_component_rules(body, fragment):
    assert has(check(meta(), body=body), fragment)


def test_status_is_product_only():
    m = meta(track="regulatory", isRegulatoryAdjacent=True)
    errs = check(m, body='<Status tone="danger">Out of service</Status>', track_dir="regulatory")
    assert has(errs, "product pages only")


def test_tags_in_code_are_text():
    body = "Write `<Button>` like this:\n\n```mdx\n<OutcomeSummary />\n```"
    assert check(meta(), body=body) == []


CAPTURE = '<Capture frame="record-hl-214-pm-sent-4">The service record with its faults found</Capture>'


@pytest.mark.parametrize("track", ["product", "maintenance", "regulatory", "business"])
def test_capture_on_its_own_line_passes_on_any_track(track):
    m = meta(track=track, isRegulatoryAdjacent=track == "regulatory")
    assert check(m, body=f"How it is recorded:\n\n{CAPTURE}\n\nMore prose.", track_dir=track) == []


@pytest.mark.parametrize("body", [
    f"See {CAPTURE} here.",
    f"## {CAPTURE}",
    '<Capture frame="console-work-1" />',
    "<Capture frame={x}>Words</Capture>",
    '<Capture frame="Console_Work">Words</Capture>',
    '<Capture frame="console-work-1">The {list}</Capture>',
    '<Capture frame="console-work-1">The *Work* list</Capture>',
])
def test_capture_rules(body):
    assert has(check(meta(), body=body), "not a knowledge-base component")


def test_capture_not_in_qa():
    m = meta(kind="faq", qa=[{"question": "Q?", "answer": CAPTURE}])
    assert has(check(m), "must not contain components")


def test_status_not_in_qa():
    m = meta(kind="faq", qa=[{"question": "Q?", "answer": 'It reads <Status tone="success">Passed</Status>.'}])
    assert has(check(m), "must not contain components")


# ---------------------------------------------------------------------------
# Click-path check
# ---------------------------------------------------------------------------
def start(target="/start/x"):
    return {"kind": "start", "target": target, "text": "Go"}


def related(target):
    return {"kind": "related", "target": target, "text": "See"}


def corpus(**steps):
    """slug -> meta; a value of None leaves nextStep out."""
    return {s: ({"slug": s} if st is None else {"slug": s, "nextStep": st})
            for s, st in steps.items()}


def test_click_direct_start_passes():
    assert v.check_click_paths(corpus(a=start())) == {}


def test_click_related_then_start_passes():
    assert v.check_click_paths(corpus(a=related("b"), b=start())) == {}


def test_click_three_clicks_fails():
    out = v.check_click_paths(corpus(a=related("b"), b=related("c"), c=start("/start/x")))
    assert out == {"a": "3 clicks to /start (limit 2): a -> b -> c -> /start/x"}


def test_click_loop_fails():
    out = v.check_click_paths(corpus(a=related("b"), b=related("a")))
    assert out == {"a": "loop: a -> b -> a", "b": "loop: b -> a -> b"}


def test_click_three_page_cycle_fails():
    out = v.check_click_paths(corpus(a=related("b"), b=related("c"), c=related("a")))
    assert out["a"] == "loop: a -> b -> c -> a"
    assert set(out) == {"a", "b", "c"}


def test_click_feeder_into_loop_fails():
    out = v.check_click_paths(corpus(f=related("a"), a=related("b"), b=related("a")))
    assert out["f"] == "loop: f -> a -> b -> a"


def test_click_kind_none_fails():
    assert v.check_click_paths(corpus(a={"kind": "none"})) == {"a": "nextStep kind is none"}


def test_click_absent_next_step_fails():
    assert v.check_click_paths(corpus(a=None)) == {"a": "no nextStep"}


def test_click_chain_through_page_without_step_fails():
    out = v.check_click_paths(corpus(a=related("b"), b=None))
    assert has([out["a"]], "chain reaches b") and has([out["a"]], "no nextStep")


def test_click_dangling_target_not_double_reported():
    out = v.check_click_paths(corpus(a=related("zzz"), up=related("a"), ok=start()))
    assert "a" not in out
    assert out["up"] == "chain reaches unknown page: up -> a -> zzz"
    assert "ok" not in out


def test_click_malformed_step_not_double_reported():
    assert v.check_click_paths(corpus(a={"kind": "cta"})) == {}
    assert v.check_click_paths(corpus(a="oops")) == {}


def test_click_error_names_file_in_repo_walk(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", FRONT_NO_STEP)
    assert v.validate_content(content) == ["content/product/alpha.mdx: no nextStep"]


def _self_ref_front():
    return FRONT.format(slug="alpha").replace(
        STEP_BLOCK, "nextStep:\n  kind: related\n  target: alpha\n  text: See\n"
    )


def test_self_referencing_page_reported_once(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", _self_ref_front())
    errs = v.validate_content(content)
    assert len(errs) == 1 and "own slug" in errs[0]


def test_self_referencing_page_not_stale_when_allowlisted(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", _self_ref_front())
    errs = v.validate_content(content, {"alpha": "x"})
    assert len(errs) == 1 and "own slug" in errs[0] and "remove it" not in errs[0]


def test_allowlisted_page_passes_with_note(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", FRONT_NO_STEP)
    notes: list[str] = []
    assert v.validate_content(content, {"alpha": "backfill pending"}, notes) == []
    assert len(notes) == 1 and "alpha.mdx" in notes[0] and "backfill pending" in notes[0]


def test_stale_allowlist_entry_fails(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", FRONT.format(slug="alpha"))
    errs = v.validate_content(content, {"alpha": "backfill pending"})
    assert len(errs) == 1 and "already meets" in errs[0] and "remove it" in errs[0]


def test_unknown_allowlist_slug_fails(tmp_path):
    content = tmp_path / "content"
    write(content / "product" / "alpha.mdx", FRONT.format(slug="alpha"))
    errs = v.validate_content(content, {"gone": "backfill pending"})
    assert len(errs) == 1 and "`gone` is not a page" in errs[0]


def test_committed_allowlist_matches_the_corpus():
    allow = v.load_click_path_allowlist()
    notes: list[str] = []
    root = Path(__file__).resolve().parents[1] / "content"
    assert v.validate_content(root, allow, notes) == []
    assert len(notes) == len(allow)
