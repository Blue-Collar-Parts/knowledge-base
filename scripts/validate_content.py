#!/usr/bin/env python3
"""Validate the knowledge base content.

Checks front matter against the rules in README.md, internal links, and that
page text carries no figures from private data classes.

Usage: python3 scripts/validate_content.py [content-dir]
Exit status: 0 when every page passes, 1 otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

TRACKS = ("regulatory", "product", "maintenance", "business")
KINDS = ("article", "faq")
STATUSES = ("available", "in-development")
NEXT_STEP_KINDS = ("related", "start", "none")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CFR_RE = re.compile(r"^49 CFR (Part 396 Appendix A|\d{3}\.\d+(\([a-z0-9]+\))*)$")
START_TARGET_RE = re.compile(r"^/start(/[a-z0-9]+(-[a-z0-9]+)*)?$")

TOPICS_FILE = Path(__file__).resolve().parents[1] / "vocabulary" / "topics.json"


def load_topic_vocabulary(path: Path = TOPICS_FILE) -> set[str]:
    return set(json.loads(path.read_text(encoding="utf-8"))["topics"])

# Link text that must not appear as a next step: the brand call to action, and
# wording that claims compliance.
BRAND_CTA = "build your record"
COMPLIANCE_CLAIM_RE = re.compile(r"complian|satisf|certif|396\.17", re.IGNORECASE)


class _Loader(yaml.SafeLoader):
    """SafeLoader that leaves dates as strings so they can be format-checked."""


_Loader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


# ---------------------------------------------------------------------------
# Private-data number scan
#
# Page text must not carry a figure from a class of data Blue Collar Parts
# keeps private. A sentence fails when it holds a number and a term from one of
# these classes. Aggregate mixes computed from public FMCSA inspection data do
# not use these terms, so they pass; README "Rules for analysis of public FMCSA
# data" governs how they are worded.
# ---------------------------------------------------------------------------
PRIVATE_CLASS_TERMS: dict[str, re.Pattern[str]] = {
    "search volume": re.compile(
        r"search(?:es)?\s+volume|keyword\s+volume|monthly\s+searches|"
        r"searches\s+(?:per|a|each)\s+month|monthly\s+search\b",
        re.IGNORECASE,
    ),
    "keyword difficulty": re.compile(r"keyword\s+difficulty", re.IGNORECASE),
    "cost per click": re.compile(r"\bCPC\b|cost[- ]per[- ]click|\bbids?\b", re.IGNORECASE),
    "impressions": re.compile(r"\bimpressions?\b|click[- ]through", re.IGNORECASE),
    "clicks": re.compile(r"\bclicks?\b", re.IGNORECASE),
    "sessions": re.compile(r"\bsessions?\b", re.IGNORECASE),
    "visitors": re.compile(r"\bvisitors?\b|\bpage\s*views?\b", re.IGNORECASE),
    "signups": re.compile(r"\bsign-?ups?\b", re.IGNORECASE),
    "conversion rate": re.compile(r"conversion\s+rates?", re.IGNORECASE),
    "score": re.compile(
        r"\b(?:opportunity|priority|keyword|demand)\s+scores?\b", re.IGNORECASE
    ),
    "technician share": re.compile(
        r"technician\s+(?:share|weight)|(?:share|weight)\s+of\s+technicians",
        re.IGNORECASE,
    ),
}

# Business figures of Blue Collar Parts itself: the company name and a
# revenue or customer-count term in the same sentence.
COMPANY_RE = re.compile(r"Blue\s+Collar\s+Parts|\bBCP\b", re.IGNORECASE)
BUSINESS_TERM_RE = re.compile(
    r"\b(?:revenue|customers|users|accounts|MRR|ARR)\b", re.IGNORECASE
)

# A figure: digits (with separators, decimals, percent) or a scale word.
NUMBER_RE = re.compile(
    r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?|\b(?:thousand|million|billion)\b", re.IGNORECASE
)


def _sentences(text: str) -> list[str]:
    parts: list[str] = []
    for line in text.splitlines():
        parts.extend(re.split(r"(?<=[.!?])\s+", line))
    return [p for p in parts if p.strip()]


def _strip_for_scan(text: str) -> str:
    """Drop link targets and URLs so path digits are not read as figures."""
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def scan_private_numbers(text: str) -> list[str]:
    """Return one message per sentence that pairs a number with a private class."""
    found: list[str] = []
    for sentence in _sentences(_strip_for_scan(text)):
        if not NUMBER_RE.search(sentence):
            continue
        for name, rx in PRIVATE_CLASS_TERMS.items():
            if rx.search(sentence):
                found.append(f'number next to "{name}" term: {sentence.strip()[:100]}')
                break
        else:
            if COMPANY_RE.search(sentence) and BUSINESS_TERM_RE.search(sentence):
                found.append(
                    "number next to Blue Collar Parts business term: "
                    f"{sentence.strip()[:100]}"
                )
    return found


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------
def split_front_matter(raw: str) -> tuple[dict | None, str, str | None]:
    """Return (meta, body, error)."""
    if not raw.startswith("---"):
        return None, raw, "missing front matter"
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", raw, re.DOTALL)
    if not match:
        return None, raw, "unterminated front matter"
    try:
        meta = yaml.load(match.group(1), Loader=_Loader)
    except yaml.YAMLError as exc:
        return None, match.group(2), f"front matter is not valid YAML: {exc}"
    if not isinstance(meta, dict):
        return None, match.group(2), "front matter is not a mapping"
    return meta, match.group(2), None


def _is_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_date(value: object) -> bool:
    return isinstance(value, str) and bool(DATE_RE.match(value))


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _str_list(value: object) -> bool:
    return isinstance(value, list) and all(_is_str(v) for v in value)


def _non_code_body(body: str) -> str:
    """Body text with fenced code blocks removed."""
    out: list[str] = []
    fenced = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def _kb_link_slugs(body: str) -> list[str]:
    slugs: list[str] = []
    text = _non_code_body(body)
    for target in re.findall(r"\]\(\s*([^)\s]+)", text):
        target = target.split("#", 1)[0].split("?", 1)[0]
        if target.startswith("/kb/"):
            slug = target[len("/kb/"):].rstrip("/")
        elif re.fullmatch(r"[a-z0-9][a-z0-9-]*", target):
            slug = target
        else:
            continue
        slug = re.sub(r"\.(md|json)$", "", slug)
        if slug:
            slugs.append(slug)
    for target in re.findall(r"""href=["']/kb/([^"'#?\s]+)""", text):
        slugs.append(re.sub(r"\.(md|json)$", "", target.rstrip("/")))
    return slugs


def _text_for_scan(meta: dict, body: str) -> str:
    chunks = [str(meta.get("title", "")), str(meta.get("description", ""))]
    qa = meta.get("qa")
    if isinstance(qa, list):
        for item in qa:
            if isinstance(item, dict):
                chunks.append(str(item.get("question", "")))
                chunks.append(str(item.get("answer", "")))
    chunks.append(body)
    return "\n".join(chunks)


def validate_page(
    meta: dict, body: str, track_dir: str, stem: str, all_slugs: set[str]
) -> list[str]:
    errs: list[str] = []

    for field in (
        "slug", "title", "description", "track", "kind", "order",
        "isRegulatoryAdjacent", "publishedAt", "cfr",
    ):
        if field not in meta:
            errs.append(f"missing required field `{field}`")

    for field in ("slug", "title", "description"):
        if field in meta and not _is_str(meta[field]):
            errs.append(f"`{field}` must be a non-empty string")

    slug = meta.get("slug")
    if _is_str(slug) and slug != stem:
        errs.append(f"slug `{slug}` must match filename `{stem}`")

    track = meta.get("track")
    if "track" in meta:
        if track not in TRACKS:
            errs.append(f"`track` must be one of {', '.join(TRACKS)}")
        elif track != track_dir:
            errs.append(f"track `{track}` must match directory `{track_dir}`")

    if "kind" in meta and meta["kind"] not in KINDS:
        errs.append("`kind` must be `article` or `faq`")

    if "order" in meta and not _is_number(meta["order"]):
        errs.append("`order` must be a number")

    if "isRegulatoryAdjacent" in meta and not isinstance(meta["isRegulatoryAdjacent"], bool):
        errs.append("`isRegulatoryAdjacent` must be true or false")

    if "publishedAt" in meta and not _is_date(meta["publishedAt"]):
        errs.append("`publishedAt` must be YYYY-MM-DD")
    if "updatedAt" in meta and not _is_date(meta["updatedAt"]):
        errs.append("`updatedAt` must be YYYY-MM-DD")

    cfr = meta.get("cfr")
    if "cfr" in meta:
        if not isinstance(cfr, list):
            errs.append("`cfr` must be an array")
        else:
            for entry in cfr:
                if not isinstance(entry, str) or not CFR_RE.match(entry):
                    errs.append(
                        f"cfr entry {entry!r} is not in canonical form "
                        '(for example "49 CFR 396.17(c)(2)" or '
                        '"49 CFR Part 396 Appendix A")'
                    )

    if "related" in meta:
        related = meta["related"]
        if not _str_list(related):
            errs.append("`related` must be an array of slugs")
        else:
            for target in related:
                if target not in all_slugs:
                    errs.append(f"related slug `{target}` does not resolve to a page")

    if "status" in meta:
        if meta["status"] not in STATUSES:
            errs.append("`status` must be `available` or `in-development`")
        elif track != "product":
            errs.append("`status` is allowed on product pages only")

    if meta.get("kind") == "faq":
        qa = meta.get("qa")
        if not isinstance(qa, list) or not qa:
            errs.append("`kind: faq` requires a non-empty `qa` array")
        else:
            for item in qa:
                if not (
                    isinstance(item, dict)
                    and _is_str(item.get("question"))
                    and _is_str(item.get("answer"))
                ):
                    errs.append("each `qa` entry needs `question` and `answer`")
                    break

    if track == "maintenance":
        if meta.get("isRegulatoryAdjacent") is not False:
            errs.append("maintenance pages must set `isRegulatoryAdjacent: false`")
        if cfr != []:
            errs.append("maintenance pages must set `cfr: []`")

    for banned in ("canonicalUrl", "reviewedBy"):
        if banned in meta:
            errs.append(f"`{banned}` is not an allowed field")

    errs.extend(_check_topics(meta, cfr, load_topic_vocabulary()))
    errs.extend(_check_next_step(meta, stem, all_slugs))

    for linked in _kb_link_slugs(body):
        if linked not in all_slugs:
            errs.append(f"internal link to `{linked}` does not resolve to a page")

    errs.extend(scan_private_numbers(_text_for_scan(meta, body)))
    return errs


def _check_topics(meta: dict, cfr: object, vocabulary: set[str]) -> list[str]:
    if "topics" not in meta:
        return []
    topics = meta["topics"]
    if topics is None or topics == []:
        return []
    if not _str_list(topics):
        return ["`topics` must be an array of strings"]
    errs: list[str] = []
    if isinstance(cfr, list) and cfr:
        pm = [t for t in topics if t.startswith("pm_")]
        if pm:
            errs.append(
                f"`pm_*` topic {pm[0]!r} is not allowed on a page with `cfr` entries"
            )
    for topic in topics:
        if topic not in vocabulary:
            errs.append(f"topic {topic!r} is not in vocabulary/topics.json")
    dupes = sorted({t for t in topics if topics.count(t) > 1})
    for topic in dupes:
        errs.append(f"topic {topic!r} is listed more than once")
    return errs


def _check_next_step(meta: dict, stem: str, all_slugs: set[str]) -> list[str]:
    if "nextStep" not in meta:
        return []
    step = meta["nextStep"]
    if not isinstance(step, dict):
        return ["`nextStep` must be a mapping with `kind`, `target` and `text`"]
    errs: list[str] = []
    for key in step:
        if key not in ("kind", "target", "text"):
            errs.append(f"`nextStep.{key}` is not an allowed key")
    kind = step.get("kind")
    if kind not in NEXT_STEP_KINDS:
        return errs + ["`nextStep.kind` must be `related`, `start` or `none`"]
    target = step.get("target")
    text = step.get("text")

    if kind == "none":
        if "target" in step:
            errs.append("`nextStep` of kind `none` must omit `target`")
        if "text" in step:
            errs.append("`nextStep` of kind `none` must omit `text`")
        return errs

    if not _is_str(text):
        errs.append(f"`nextStep.text` is required for kind `{kind}`")
    else:
        normalized = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
        if normalized == BRAND_CTA:
            errs.append('`nextStep.text` must not be "Build your record."')
        if COMPLIANCE_CLAIM_RE.search(text):
            errs.append("`nextStep.text` must not claim compliance")

    if kind == "related":
        if not _is_str(target):
            errs.append("`nextStep.target` is required for kind `related`")
        elif target == stem:
            errs.append("`nextStep.target` must not be the page's own slug")
        elif target not in all_slugs:
            errs.append(f"`nextStep.target` `{target}` does not resolve to a page")
    else:
        if not (isinstance(target, str) and START_TARGET_RE.match(target)):
            errs.append(
                "`nextStep.target` for kind `start` must be `/start` or "
                "`/start/<lowercase-kebab>`"
            )
    return errs


# ---------------------------------------------------------------------------
# Repository walk
# ---------------------------------------------------------------------------
def validate_content(content_dir: Path) -> list[str]:
    errors: list[str] = []
    pages: list[tuple[Path, dict, str]] = []
    slug_owner: dict[str, Path] = {}

    files = sorted(
        p for p in content_dir.rglob("*") if p.suffix in (".mdx", ".md") and p.is_file()
    )
    for path in files:
        rel = path.relative_to(content_dir.parent)
        meta, body, err = split_front_matter(path.read_text(encoding="utf-8"))
        if err or meta is None:
            errors.append(f"{rel}: {err}")
            continue
        pages.append((path, meta, body))
        slug = meta.get("slug")
        if _is_str(slug):
            if slug in slug_owner:
                errors.append(
                    f"{rel}: slug `{slug}` is already used by "
                    f"{slug_owner[slug].relative_to(content_dir.parent)}"
                )
            else:
                slug_owner[slug] = path

    all_slugs = set(slug_owner)
    for path, meta, body in pages:
        rel = path.relative_to(content_dir.parent)
        track_dir = path.relative_to(content_dir).parts[0]
        for msg in validate_page(meta, body, track_dir, path.stem, all_slugs):
            errors.append(f"{rel}: {msg}")
    return errors


def main(argv: list[str]) -> int:
    content_dir = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1] / "content"
    if not content_dir.is_dir():
        print(f"content directory not found: {content_dir}", file=sys.stderr)
        return 1
    errors = validate_content(content_dir)
    if errors:
        for line in errors:
            print(f"ERROR {line}")
        print(f"\n{len(errors)} problem(s) found.")
        return 1
    count = sum(1 for p in content_dir.rglob("*") if p.suffix in (".mdx", ".md"))
    print(f"OK: {count} pages passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
