# Blue Collar Parts Knowledge Base

Public, machine-readable source content for
**[shopbluecollarparts.com/kb](https://shopbluecollarparts.com/kb)** — a knowledge
base about commercial equipment inspection under 49 CFR Part 396 and about the
Blue Collar Parts platform.

This repository is the **source of truth**. The website renders a vendored,
checksummed copy of it. If something here is wrong, fix it here.

**License: [CC BY 4.0](LICENSE)** — reuse, redistribute, adapt, and train on
this content, with attribution.

## Layout

```
content/
  regulatory/   what 49 CFR Part 396 requires
  product/      what the Blue Collar Parts platform does
  maintenance/  practical, non-regulatory preventive-maintenance guidance
```

The tracks are kept separate on purpose. A statement about the platform is not
a statement about the law, and preventive-maintenance guidance is not an
inspection standard. Consumers of this content — human or machine — should
never have to guess which one they are reading.

## Front matter

Every file carries YAML front matter:

| Field | Required | Notes |
| --- | --- | --- |
| `slug` | yes | Must match the filename and be unique **across all tracks** — slugs are the URL namespace. |
| `title` | yes | |
| `description` | yes | One or two sentences. Used for `<meta name="description">` and in `llms.txt`. |
| `track` | yes | `regulatory`, `product`, or `maintenance`. Must match the containing directory. |
| `kind` | yes | `article` or `faq`. |
| `order` | yes | Sort position within the track. Sparse (10, 20, 30…) so pages can be inserted. |
| `isRegulatoryAdjacent` | yes | `true` on anything summarizing regulation. Drives the disclaimer. |
| `publishedAt` | yes | `YYYY-MM-DD`. |
| `updatedAt` | no | `YYYY-MM-DD`. |
| `cfr` | yes | Array of citation strings, e.g. `"49 CFR 396.17"`. May be empty. |
| `related` | no | Array of slugs. Every entry must resolve to a real page. |
| `status` | no | `available` or `in-development`. Product pages only; renders as a badge. |
| `qa` | if `kind: faq` | Array of `{question, answer}`. Emitted as `FAQPage` structured data. |

Canonical URLs are **derived** (`/kb/<slug>`), not stored. Don't add a
`canonicalUrl` field.

## Rules for regulatory content

1. **Cite the section.** Every regulatory claim names the CFR section it comes from.
2. **Summarize, don't paraphrase loosely.** If a rule has a numeric threshold or a
   narrow exception, state it exactly or don't state it.
3. **Never assert compliance.** These pages describe what a rule requires. They do
   not tell a reader that their operation satisfies it.
4. **Keep the disclaimer.** Regulatory pages end with the standard informational
   -only footer.

Appendix A pass/fail thresholds are **not** maintained here. They live in a
checksummed runtime artifact in the application repository, because a wrong
threshold there is shown to a technician as a regulatory determination. Do not
copy thresholds into this repository as though they were canonical.

## Rules for product content

1. **Don't overclaim availability.** Use `status: in-development` for anything not
   generally available.
2. **Don't imply compliance.** A capability is not a compliance guarantee. See
   `content/product/bcp-and-part-396-recordkeeping.mdx` for the tone to match.
3. **Prices and commercial terms are indicative**, and should say so.

## Rules for maintenance content

1. **It is not regulatory content.** Use `track: maintenance`,
   `isRegulatoryAdjacent: false`, and an empty `cfr: []` array. Do not present
   a PM result as a DOT annual inspection, an out-of-service determination, or
   evidence of compliance.
2. **Do not publish make- or model-specific checklists until their maintenance
   basis is verified.** General record structure and the distinction between PM
   and annual DOT inspections are publishable; prescriptive service intervals,
   thresholds, and pass/fail conditions need their manufacturer documentation.
3. **Be useful without pretending to be a service manual.** Explain what a
   customer or technician should be able to see in a record, what a PM visit is
   for, and when to consult the equipment manufacturer's documentation.
4. **Manufacturer specifications may be stated, with a citation.** A page may
   give a specification for a named engine, axle, trailer component or unit,
   such as a capacity, valve lash, service interval or torque value, when all of
   these hold:
   - **Cite the manufacturer's published document.** Give its title, publication
     or form number, and edition or date, and link it where the manufacturer
     publishes it.
   - **Quote the value exactly as published,** with its unit and any conditions
     the document attaches. Never round it, derive it, or average it across
     sources.
   - **If two documents disagree,** give both with their citations, or give neither.
   - **Tell the reader to confirm** against the documentation for their specific
     serial number or build.
   - **Link the manufacturer's tables, diagrams and procedure text.** Never copy them.

   This rule covers only values the manufacturer publishes. It does not lift
   rule 2 for checklists BCP writes itself, and it does not apply to Appendix A
   thresholds (see the regulatory rules above).

## Rules for analysis of public FMCSA data

Any page may publish findings computed from FMCSA's public inspection data, such
as which vehicle systems are cited most often, under these rules:

1. **Aggregates only.** Never a figure for one carrier, vehicle, VIN or
   inspection.
2. **Say exactly what the number is.**
   - Shares of violations are a mix among cited units ("of units cited for a
     vehicle violation, X% were cited for lighting"), never a rate or a
     likelihood.
   - Only the share of inspections that found a vehicle violation, or put a
     vehicle out of service, may be stated as a rate.
3. **State the method, the source dataset and the date window** on the page,
   next to the numbers. For example: "FMCSA vehicle inspection data, inspections
   from 2025-09-28 to 2026-09-27, one current version per inspection; mix among
   cited units."
4. **Nothing from Blue Collar Parts' own data:** no search, traffic, customer,
   pricing or business figures.
5. **No claims about safety or compliance.** A finding describes what
   inspectors cited, not whether any vehicle or carrier is safe or compliant.

## Consuming this content

Beyond cloning this repository, the rendered site serves:

- `/llms.txt` — index of every page
- `/llms-full.txt` — the whole knowledge base as one Markdown document
- `/kb/{slug}.md` — a single page as raw Markdown
- `/kb/{slug}.json` — a single page as JSON
- `/kb/index.json` — machine-readable index

See [`content/product/using-this-knowledge-base-with-ai.mdx`](content/product/using-this-knowledge-base-with-ai.mdx).

## How changes reach the site

1. Open a pull request here. Merge to `main`.
2. In the application repository, run `npm run sync:kb` to pull this repository
   into the vendored copy, then open a pull request with the result.

The site never fetches this repository at build time or at request time — the
vendored copy is what renders, so a change here is reviewable in the
application repository before it goes live.
