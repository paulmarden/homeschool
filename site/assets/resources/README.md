# Our resources

Drop worksheets, notes, PDFs, images and self-contained HTML in here, then
register them so they appear on the right page:

    python tools/add_resource.py --lesson UNIT/LESSON \
        --title "Rounding practice sheet" \
        --url assets/resources/rounding-3dp.pdf \
        --kind worksheet --note "Printable, with space for working"

Then `python build.py`. Anything in this folder is copied into `site/assets/`,
so the links keep working wherever the site is served from.

`python tools/check_links.py` will tell you if a registered file is missing.
