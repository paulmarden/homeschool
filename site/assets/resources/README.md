# Our resources

**This is where resource files go.** Not `site/` — that folder is generated and
every build wipes it, so anything saved in there by hand is lost. (`build.py`
now refuses to run if it finds files it did not create, rather than deleting
them, but this is still the right home.)

Drop worksheets, notes, PDFs, images and self-contained HTML in here, then
register them so they appear on the right page:

    python tools/add_resource.py --unit estimation-and-rounding \
        --title "Rounding Studio" \
        --url assets/resources/Rounding-Studio.html \
        --kind html

Use `--lesson UNIT/LESSON` instead of `--unit` to attach to a single lesson, or
`--general` for the Resources page.

Then `python build.py`. Everything in this folder is copied to
`site/assets/resources/`, and the generated pages link to it with the right
relative path from wherever they sit. Always write the `--url` as
`assets/resources/FILE` — a leading slash breaks the link.

`python tools/check_links.py` will tell you if a registered file is missing.
