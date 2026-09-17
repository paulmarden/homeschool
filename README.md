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
| Generated pages | 162 |

Each **unit** page carries the unit description and curriculum threads, then
our resources for the unit, then the lesson sequence, with previous/next unit
navigation at the foot.

Each **lesson** page carries the pupil outcome, key learning points, keyword
definitions and equipment, then **our resources** for that lesson, then buttons
that open the starter and exit quizzes.

Oak's teacher-facing material — unit rationale, prior knowledge,
misconceptions, teaching tips — is deliberately not copied here. Every page
links to the Oak unit or lesson for that.

Quizzes open in a modal and support all four of Oak's question types (multiple
choice including select-all, short answer, matching and ordering). They mark
themselves, show per-question hints and feedback, and report a score. Every
question also has a "Show answer" disclosure, so a quiz stays answerable with
JavaScript off.

## Resources

The point of the site. Resources live in `data/resources.json` — in git, so
they are shared by every machine that clones the repo — and attach at three
levels: **general** (the Resources page), **unit**, and **lesson**. Each one
shows up on its own page and on the Resources index.

Add one without hand-editing JSON:

```bash
python tools/add_resource.py --lesson sequences/finding-the-nth-term \
    --title "nth term worksheet" --url assets/resources/nth-term.pdf \
    --kind worksheet --note "Printable, with space for working"

python tools/add_resource.py --unit constructions --title "…" --url "https://…"
python tools/add_resource.py --general --title "…" --url "https://…"
python tools/add_resource.py --list
```

Then `python build.py`. Files go in **`assets/resources/`** — never in `site/`,
which is generated output that every build wipes (`build.py` refuses to run if
it finds files it did not create, rather than deleting them). Write the `--url`
as `assets/resources/FILE`, with no leading slash; the build works out the right
relative path for each page. `--url` can also be an external link. `kind` is one of `link, html, pdf, video, worksheet, sheet,
notebook, book` and drives the tag; entries split into **Relevant links**
(references we use) and **Our resources** (things we made or keep), which you
can force with `--group`.

The seven links seeded in `general` are starting points — replace them with
whatever you actually use. `python tools/check_links.py` flags any registered
file that is missing.

## Progress

Exit quiz scores are saved to `localStorage` under `y8hub.progress.v1`, and
show up as a score tag on each lesson row, an "n of m done" count on the unit
page, and a per-unit count on the subject page. A lesson counts as done once
its exit quiz has been answered in full.

This is per-browser and per-device — nothing is uploaded, and clearing site
data clears it. The About page has a button to reset it deliberately.

## Layout

```
build.py               generates site/ from data/curriculum.json
data/curriculum.json   the imported curriculum (1.6 MB)
data/resources.json    our resources, attached to lessons / units / general
assets/
  ds/styles.css        Modernist design system, vendored verbatim
  site.css             site layer, built only on Modernist tokens
  quiz.js              quiz modals + live marking (progressive enhancement)
  progress.js          exit quiz scores in localStorage
  resources/           our own files, copied into the built site
tools/
  import_oak.py        re-imports the curriculum from thenational.academy
  flight.py            parser for Next.js RSC payloads
  add_resource.py      register a resource without hand-editing JSON
  fetch_images.py      optional: vendor quiz images for offline use
  check_links.py       verifies every internal link resolves
site/                  generated output — wiped and rebuilt every run;
                       never save anything here by hand
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

The quiz modal is the system's `.dialog` pattern widened for a quiz: surface
chrome top and bottom, ground behind the questions, zero radius, `--shadow-lg`.

## Content and licence

Curriculum content kept here — unit and lesson titles, outcomes, key learning
points, keywords and the quizzes — is from
[Oak National Academy](https://www.thenational.academy/) and is used under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
This site is not affiliated with or endorsed by Oak National Academy.

Oak's videos, slide decks and worksheets are **not** reproduced here — every
unit and lesson page links back to its source page so you can use them there.
