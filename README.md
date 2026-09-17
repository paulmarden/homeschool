# Year 8 Study Hub

A static homeschool study site built alongside the **Oak National Academy Year 8
maths curriculum** — all 10 units, all 148 lessons, with every starter and exit
quiz answerable in the browser.

Built to the *Homeschool Resources Wireframe* on the **Modernist** design system
from Claude Design.

## Quick start

```bash
python build.py && python -m http.server 4173 --directory site
```

Then open <http://localhost:4173>. No dependencies beyond Python 3 — no npm, no
framework, no build toolchain.

## What's in it

| | |
| --- | --- |
| Units | 10 |
| Lessons | 148 |
| Quiz questions | 1,776 |
| Generated pages | 161 |

Each **unit** page carries Oak's unit description, "why this, why now"
rationale, prior-knowledge requirements and curriculum threads, then the full
lesson sequence.

Each **lesson** page carries the pupil outcome, key learning points, keyword
definitions, common misconceptions with the suggested teacher response,
teaching tips and equipment — followed by the starter and exit quizzes.

Quizzes support all four of Oak's question types (multiple choice including
select-all, short answer, matching and ordering). They mark themselves, show
per-question hints and feedback, and report a score. Every question also has a
"Show answer" disclosure, so the page is fully usable with JavaScript off.

## Layout

```
build.py               generates site/ from data/curriculum.json
data/curriculum.json   the scraped curriculum (1.7 MB)
assets/
  ds/styles.css        Modernist design system, vendored verbatim
  site.css             site layer, built only on Modernist tokens
  quiz.js              live quiz marking (progressive enhancement)
tools/
  import_oak.py        re-scrapes the curriculum from thenational.academy
  flight.py            parser for Next.js RSC payloads
  fetch_images.py      optional: vendor quiz images for offline use
  check_links.py       verifies every internal link resolves
site/                  generated output — safe to delete and rebuild
```

`site/` is committed so the site can be served or published without running the
build.

## Refreshing the curriculum

```bash
python tools/import_oak.py    # writes curriculum.json next to itself
python build.py
python tools/check_links.py
```

`import_oak.py` caches every fetched page, so re-runs are cheap; delete its
`cache/` directory to force a full refetch.

## Quiz images

670 quiz questions include diagrams, which by default hotlink Oak's CDN. To make
the site work offline:

```bash
python tools/fetch_images.py && python build.py
```

That vendors the 564 unique images into `assets/quiz-images/`; the build detects
the manifest and rewrites the image sources automatically. Delete the directory
to go back to hotlinking.

## Design system

`assets/ds/styles.css` is the Modernist stylesheet, copied verbatim from the
Claude Design project — don't hand-edit it; re-sync it instead. Everything in
`site.css` is built from its tokens (`--color-*`, `--font-*`, `--space-*`,
`--radius-*`, `--shadow-*`), with no hard-coded hex values, font names or radii,
so retuning the design system retunes the whole site.

Two deliberate departures from the system's written guidance, both narrow:

- **Quiz diagrams are not greyscaled.** The system sends every content image
  through `.grayscale`, but that rule is about photography; these are number
  lines and graphs where colour can carry meaning.
- **Single-answer quiz options use a round marker.** Modernist is zero-radius
  throughout, but its own `.radio .dot` is a circle — the shape is what
  distinguishes "pick one" from "select all".

## Content and licence

Curriculum content is from [Oak National Academy](https://www.thenational.academy/)
and is used under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
This site is not affiliated with or endorsed by Oak National Academy.

Oak's videos, slide decks and worksheets are **not** reproduced here — every
unit and lesson page links back to its source page so you can use them there.
