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
  figures/      not a track: image files for data figures and page images
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
| `image` | no | Articles only. One to three PNG paths in `figures/`, one per aspect ratio. See [Data figures and page images](#data-figures-and-page-images). |

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
5. **Show the screen, drawn from code.** Any page may place a screen of the
   product, alone on its own line:

   ```mdx
   <Demo screen="record" />
   ```

   The website draws the screen from code on sample data and puts the label
   "Example record · sample data" on it. It is never a screenshot and never a
   real customer's record. Do not add screenshots of the product to the
   knowledge base. The only image files are the data figures and page images in
   `content/figures/`; see
   [Data figures and page images](#data-figures-and-page-images).

   `screen` is one of `record`, `calendar`, `customer`, `asset`, `walk`,
   `send`, `maintenance-status` or `annual-form` (an annual inspection on its
   form). Use each screen at most once per page. The
   tag takes no children and no other attributes: bcp-web owns each screen's
   caption words (`lib/kb-demos.ts`), so write the prose around it to stand
   on its own. The validator rejects an unknown screen, a screen used twice on a
   page, a tag inline or in a heading, and any component in `qa`. On a
   maintenance or regulatory page, keep a screen in its own short section about
   how Blue Collar Parts records the work, never inside the regulatory or
   maintenance guidance, and claim nothing about compliance.

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

## Data figures and page images

A page may show its own data as a picture, but only with a text twin: the
markdown table directly under the picture states everything the picture shows.
Readers and machines that cannot see the picture read the table, and the `.md`
and `.json` copies and `llms-full.txt` keep the caption, the source line and the
table but drop the picture.

The twin says everything. A reader who never sees the picture loses nothing,
and a fact that is only in the picture is a mistake on the page. The twin sits
in the page body, never behind a tab or an accordion.

### What each format is for

A page uses a format only when it answers the page's question, never because
this list allows it.

| Format | What it is for | Its text twin | Pages that use it |
| --- | --- | --- | --- |
| Spec table | A manufacturer's value, one row per engine generation or model year, each row citing its document (maintenance rule 4). | It is text. | Spec pages |
| Requirement table | What a rule requires: what, who, how often, how long to keep it. Each row cites its CFR section and links eCFR, and no row restates an Appendix A threshold. | It is text. | Regulatory and form pages |
| Checklist table | The items a visit covers, in an order a technician can work from (maintenance rule 2). | It is text. | Generator and marine, form, spec and problem pages; on a spec page, only where the manufacturer's document gives one |
| Data figure (`<KbDataFigure>`) | One finding from FMCSA's public inspection data, shown as a horizontal bar mix. | The table directly under it, with each row's count. | Problem and data pages |
| Page image (`image`) | The page's share image. Today that is a spec card: one engine, its headline value and the source document. | The spec table at the top of the page. The card shows nothing the table does not. | Spec pages about one engine |
| Product screen (`<Demo>`) | The product's own screen, drawn from code on sample data (product rule 5). | The prose around it; on a form page, also the requirement or checklist table. | Any track |
| Status badge (`<Status>`) | A record's state, in the record's own words (product rule 4). | Its words. | Product track |

The validator checks the tags and files below. Which format a page type
carries is checked in review: the validator accepts `image` on any article,
but review keeps it to one-engine spec pages, and a page that names two
engines carries no card. A form page never promises a PDF, a printable
template or a download; its requirement or checklist table answers those
searches.

### The `<KbDataFigure>` tag

```mdx
<KbDataFigure src="figures/cited-systems.png" alt="Among cited units, brakes lead at 30.0%. The table below gives each system." caption="Among cited units, 30.0% were cited for brakes." source="FMCSA vehicle inspection data, inspections 2025-09-28 to 2026-09-27, cited units" asOf="2026-09-27" table="cited-systems" tableCaption="Cited units by system" />

| System | Cited units | Share of cited units |
| --- | ---: | ---: |
| Brakes | 1,200 | 30.0% |
```

The tag takes exactly these attributes, each required and non-empty:

| Attribute | What it holds |
| --- | --- |
| `src` | The image file: `figures/<name>.png` or `figures/<name>.svg`, a kebab-case name in `content/figures/`. Never a URL or a `..` path. The file must exist and pass the image-file rules below. |
| `alt` | The finding, not the picture, ending by naming the table under it ("… the table below gives each system."). See rule 5 under [Captions, alt text and the numbers](#captions-alt-text-and-the-numbers). |
| `caption` | The finding the figure states. |
| `source` | The dataset, the inspection window and the population the figure is drawn from. |
| `asOf` | The data date, a real `YYYY-MM-DD` date. |
| `table` | A kebab-case id for the twin table, unique on the page. Neither the id nor `<id>-caption` may equal the id of a `##` heading on the page. |
| `tableCaption` | What the table holds, shown above it. |

The validator rejects:

- any other attribute, an attribute given twice, an empty one, or a value with
  a double quote or a backtick in it;
- a tag that does not start at the beginning of its own line and end with
  `/>` (only spaces or tabs may follow), including one that is indented, in a
  heading, in a paragraph, in inline code, or with children. To show the tag as
  an example, put it in a fenced code block;
- a figure whose next block is not a markdown table: a header row, then a
  delimiter row with the same number of cells. A twin table has at most 8
  columns;
- any component, a figure included, in `qa`.

Right-align a number column (`---:`) so the site end-aligns it; the validator
does not check this. The rules for the page's track apply to a figure as they
do to prose: the caption, source and table say exactly what the number is.

### Captions, alt text and the numbers

These hold for the figure, its table, its caption and its alt text alike, on
top of the [rules for analysis of public FMCSA data](#rules-for-analysis-of-public-fmcsa-data).
The validator checks that the alt text ends by naming the table, and its
private-number scan covers a figure's caption, alt text and table like any
other page text. Review checks the rest.

1. **Real numbers only.** Every bar is a value computed from FMCSA's public data
   on a stated date. None is typed in, and none is carried over from an older
   window without saying so. Give shares to one decimal place, and make the
   picture show exactly the table's values.
2. **The window is on the figure.** The source line gives the dataset, the
   inspection window and the population, for example "FMCSA vehicle inspection
   data, inspections 2025-10-19 to 2026-10-18, cited tractors".
3. **Every row carries its count.** When a figure compares bands, the caption
   gives the smallest and largest count. A band with no data reads "not enough
   data", never zero.
4. **The caption's first sentence is the finding, in words,** using the mix
   wording: "Among cited tractors aged 15 or more, X% had a lighting
   violation." Never "more likely", "at risk", "riskier", "safer", "clean",
   "compliant", "passed" or "certified", and no verb that implies a trend or a
   cause, such as "rises", "increases" or "drives". Give the values and let the
   reader compare them. A rate appears only where FMCSA rule 2 allows one.
5. **Alt text states the finding, not the picture.** "Bar chart" is not alt
   text. Name the population and the unit of every band ("cited tractors aged
   0–2 years"), give the finding and the range, and end by naming the table
   that holds the full rows.
6. **Bars follow the table,** in its row order: age bands youngest first,
   categories largest first. Use at most eight bars, and label every value.
7. **Bars carry no status colour.** Use a data colour or a neutral, never
   green and never a status tone. Status colours appear only on a record's
   state (`<Status>`, `<Demo>`).

### Image files

Every file in `content/figures/` is a kebab-case `.png` or
`.svg` and declares its provenance as an IPTC `DigitalSourceType` in its XMP
metadata (`http://cv.iptc.org/newscodes/digitalsourcetype/<code>`): a chart
drawn from data is `dataDrivenMedia`, a generated image
`trainedAlgorithmicMedia` (any code in the IPTC list is accepted; these are
the two to use). In a PNG, write the XMP as an uncompressed `iTXt`
chunk so it can be read. An SVG gives its size (`width` and `height`, or a
`viewBox`) and is a plain drawing: no `<script>`, event handler (`on…=`),
`<foreignObject>`, `href` or `url()` to anything but a `#` fragment in the same
file, `@import`, `javascript:` or `<!ENTITY`. The folder holds no
subdirectories.

### Page images

An article may name its share images in front matter:

```yaml
image:
  - figures/cited-systems.png
  - figures/cited-systems-4x3.png
  - figures/cited-systems-1x1.png
```

One to three PNG files from `content/figures/`, each listed once, each at least
50,000 pixels, and each 16:9, 4:3 or 1:1, with one file per ratio. The 16:9 file
comes first; it is the page's share image. FAQ pages take no `image`.

A page image is shown on the page. The 16:9 file is the PNG of a
`<KbDataFigure>` on the same page, with the same file name:
`figures/cited-systems.png` goes with a figure whose `src` is
`figures/cited-systems.png` or `figures/cited-systems.svg`. The 4:3 and 1:1
files are crops of it, named `<name>-4x3.png` and `<name>-1x1.png`, each after
its own ratio. The validator checks the names; review checks that each crop
really is the figure.

### Every image

Every image, figure or page image, also follows these rules. Review checks
them; the validator's file rules are under [Image files](#image-files).

- **Made for its page.** An image states that page's own finding or value. Do
  not use a template image repeated across pages, a stock photo or a
  decorative header.
- **No manufacturer logos, photographs or diagrams.** Link them where the
  manufacturer publishes them, and never copy them onto a card or a page
  (maintenance rule 4).
- **No screenshots and no look-alikes of the product.** The product appears
  only as a `<Demo>` screen drawn from code (product rule 5). An illustration,
  a generated image or a hand-built copy of a product screen is not allowed.
- **No new colours.** Use the site's existing data colours and neutrals.

The slug `figures` is reserved, because `/kb/figures/` serves the image files.

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
