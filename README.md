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
  business/     practical guidance for technicians who run a service business
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
| `track` | yes | `regulatory`, `maintenance`, `business`, or `product`. Must match the containing directory. |
| `kind` | yes | `article` or `faq`. |
| `order` | yes | Sort position within the track. Sparse (10, 20, 30…) so pages can be inserted. |
| `isRegulatoryAdjacent` | yes | `true` on anything summarizing regulation. Drives the disclaimer. |
| `publishedAt` | yes | `YYYY-MM-DD`. |
| `updatedAt` | no | `YYYY-MM-DD`. |
| `cfr` | yes | Array of citation strings in the canonical form below. May be empty. |
| `related` | no | Array of slugs. Every entry must resolve to a real page. |
| `topics` | no | Array of topic values from the controlled vocabulary in `vocabulary/topics.json`. See [Topics, next step and citations](#topics-next-step-and-citations). |
| `nextStep` | yes | One next step for the reader: `kind` (`related` or `start`; `none` fails the click-path check), `target`, `text`. See the rules below. |
| `status` | no | `available` or `in-development`. Product pages only; renders as a badge. |
| `qa` | if `kind: faq` | Array of `{question, answer}`. Emitted as `FAQPage` structured data. |

Canonical URLs are **derived** (`/kb/<slug>`), not stored. Don't add a
`canonicalUrl` field.

### Topics, next step and citations

**`cfr` citation form.** Each entry is `49 CFR <part>.<section>` with any
paragraph letters or numbers in parentheses and no spaces, or
`49 CFR Part 396 Appendix A`. Passing: `49 CFR 396.17`, `49 CFR 396.17(c)(2)`,
`49 CFR 393.47(e)`, `49 CFR Part 396 Appendix A`. Failing:
`49 CFR Part 396, Appendix A`, `49 CFR §396.17`, `CFR 396.17`,
`49 CFR 396.17 (c)`.

**`topics`.** Topic values come from a controlled vocabulary maintained by
Blue Collar Parts and kept in `vocabulary/topics.json`, which is updated when
the vocabulary changes. Each value must be in that list and may appear once per
page. The current values are `aftertreatment_dpf`, `brakes_air`,
`tires_wheels`, `lighting_electrical`, `engine`, `periodic_inspection`,
`pm_truck_otr`, `chassis_trailer_body`, `inspector_qualification`,
`suspension`, `driver_inspection`, `roadside_enforcement`, `refrigeration`,
`pm_diesel_genset` and `pm_marine_diesel`. A topic whose value starts with `pm_`
is never allowed on a page that lists `cfr` entries.

**`nextStep`.** Every page carries one next step, shown as a single link at the
end of the page. The click-path standard below decides which one.

```yaml
nextStep:
  kind: related          # related | start | none
  target: air-brake-system
  text: "See how an air brake system works"
```

- `related`: `target` is the slug of another page, and not the page's own slug.
  `text` is required.
- `start`: `target` is `/start` or `/start/<name>`, with `<name>` in lowercase
  letters, digits and hyphens. `text` is required. Use it only where the product
  offers that work today. The annual inspection is offered on trucks and
  trailers, so a regulatory page about it may point at `/start/annual-inspection`.
- `none`: omit `target` and `text`. The schema allows it, but a page with it
  fails the click-path check below.
- `text` is plain, descriptive link text. It is never "Build your record." and
  never says a record satisfies or complies with a regulation.

**Click-path standard (provisional).** Every page must reach its best-fit
`/start` or `/start/<feature>` page in at most 2 clicks, and in 1 click where a
direct link fits. Clicks are counted by following `nextStep` only:

- a `start` step is 1 click;
- each `related` step before it adds 1, so a `related` step to a page whose own
  step is `start` is 2 clicks;
- 3 or more clicks is over the standard.

A page fails when it has no `nextStep`, has `kind: none`, sits in a loop, points
(directly or down its chain) at a page that does not exist, or needs more than 2
clicks. The "Then:" line in a page body and the `related` front-matter array are
not paths and are never counted.

The limit of 2 is provisional. It will be revisited once reader click rates on
next-step links exist to set it from.

Author checklist for a new page:

- Pick the best-fit `/start` or `/start/<feature>` target while writing the
  page, for example `/start/condition-report`, `/start/annual-inspection` or
  `/start/vin-decode`. Plain `/start` is for pages where no feature fits.
- Do not leave `nextStep` for later. CI fails a page without a path.
- A problem or maintenance page may carry a `start` step directly, or one
  `related` step to a feature page that itself carries a `start` step. Do not
  chain further.

**Allowlist.** `scripts/click_path_allowlist.json` maps a page slug to the
reason it is temporarily excused from the check. An allowlisted page that fails
passes with a `NOTE` line giving its reason, and the summary counts them. The
check fails if an allowlisted slug is not a page, or if the page already meets
the standard: remove the entry then, so the list only shrinks. The allowlist is
temporary and must be empty once the existing pages have a path. Do not add an
entry to excuse a new page; if one is ever added, the pull request must state
the reason.

**Generated by the site, never written in a page.** Do not hand-write eCFR links
for `cfr` citations, edition dates, a "reviewed" line, or the statement of what
Blue Collar Parts does on a page. The site produces them. There is no
`reviewedBy` field.

**Checks.** A public workflow runs `scripts/validate_content.py` on every pull
request. It checks the front matter and the rules above, that internal links
(`/kb/<slug>`) resolve, that every page meets the click-path standard, and that
page text does not pair a number with
Blue Collar Parts' own private figures (search or keyword data, traffic,
sign-ups, scores, revenue or customer counts). Aggregates of public FMCSA data
are not affected. Run it locally:

```sh
pip install -r requirements-dev.txt
python3 -m pytest -q
python3 scripts/validate_content.py
```

## Rules for every page

These apply on every track, in addition to the track rules below. They follow
Google Search's guidance on
[AI-generated content](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)
and on
[generative AI features](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide).
Pages here are drafted with AI. That is not a problem in itself; publishing
many pages that add nothing for the reader is.

1. **Nothing on a page implies a person wrote or reviewed it.** Don't invent a
   reviewer, a credential, or first-hand experience ("in our experience", "our
   technicians found"). There is no `reviewedBy` field.
2. **Fact-check the whole page, front matter included.** `title` and
   `description` become the page title, the meta description and the
   structured data, so they get the same check as the body. Regulatory claims
   cite their section (see the regulatory rules).
3. **One page per job or topic, never one page per way of asking it.** A new
   page answers a question no existing page answers. A variant of a question
   an existing page already covers becomes a question-shaped section on that
   page. Don't repeat a section word for word across pages.
4. **Prefer what only this knowledge base can say.** Exact citations, the
   structure of a real service record, and analysis the reader cannot get
   elsewhere add value. A general summary that any model could write adds
   little.
5. **Write for the technician, not for AI search.** Lead each section with a
   direct answer under a heading phrased the way a technician would ask it.
   Use the technician's own words ("checklist", "form", "slack adjuster").
   Don't split a page into fragments, and don't add wording or markup "for AI
   Overviews" or "for the featured snippet". `llms.txt` and the `.md` and
   `.json` copies serve other assistants; Google Search ignores them.
6. **Keep the answer visible.** Don't put body text, FAQ answers included,
   behind accordions or tabs.
7. **Choose `faq` or `article` by what reads best,** never for a rich result.
   Google no longer shows FAQ rich results.
8. **No ratings, reviews, testimonials or star scores** on any page or in its
   front matter. The site builds structured data from front matter and the
   rendered page, so front matter describes only what the page shows.
9. **Dates are real.** `publishedAt` is the day the page goes live.
   `updatedAt` changes only when the content changes, never to make a page
   look fresh.

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
4. **Show a state the way the record shows it.** A product page may use one
   component, the service record's status badge:

   ```mdx
   <Status tone="success">Passed</Status>
   ```

   `tone` is `neutral`, `info`, `success`, `warning` or `danger`, and the words
   are the record's own words for that state. The site renders the badge with
   its color and shape. The `.md` and `.json` copies and `llms-full.txt` keep
   only the words, so the words must say the state on their own. The validator
   rejects any other component, `<Status>` outside the product track or in a
   heading, and any component in `qa`. See
   `content/product/reading-a-service-record.mdx`.
5. **Show the screen, from the demonstration account.** Any page may place a
   screen of the product, alone on its own line:

   ```mdx
   <Capture frame="record-hl-214-pm-sent-4">The service record for a tractor PM, sent with its faults found</Capture>
   ```

   The frames are captures of the seeded demonstration account, never a real
   customer's record. The website keeps them and the list of names
   (bcp-web `lib/kb-captures.ts`); they are not part of this repository or its
   license. The site puts the label "Example record · sample data" on the frame.
   The words are the image's alt text and caption, and the only thing the `.md`
   and `.json` copies and `llms-full.txt` keep, so they must describe the screen
   on their own and say only what it shows. On a maintenance or regulatory
   page, keep a capture in its own short section about how Blue Collar Parts
   records the work, never inside the regulatory or maintenance guidance, and
   claim nothing about compliance. A new frame lands in bcp-web before a page
   that names it is synced.

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

## Rules for business content

1. **It is general guidance, not legal, tax, insurance, or financial advice.**
   Say so in the footer, and point to the State, local agency, or licensed
   professional who decides the specific question.
2. **Publish no market rates, incomes, or outcomes.** Show how to build a price
   or a plan; do not promise what it will earn.
3. **Name no carriers, vendors, or competitors** as recommendations.

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
