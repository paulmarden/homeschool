# Our resources

**This is where resource files go.** Not `site/` — that folder is generated and
every build wipes it. (`build.py` now refuses to run if it finds files it did
not create, rather than deleting them, but this is still the right home.)

## Layout

One folder per unit, holding that unit's resources *and* those of every lesson
in it — so a unit's material stays together instead of spreading across 148
lesson folders:

    assets/resources/
      general/                                  shown on the Resources page
      maths/year-8/estimation-and-rounding/
      maths/year-8/sequences/
      ...

`python tools/init_resource_dirs.py` creates the tree and is safe to re-run
after adding units or a new subject.

**Dropping a file in here is not enough on its own** — the pages only render
what is registered in `data/resources.json`, so an unregistered file is copied
into the build but nothing links to it. `build.py` lists any it finds.

## Adding a resource

Easiest — hand it the file and it goes in the right folder for you:

    python tools/add_resource.py --lesson sequences/finding-the-nth-term \
        --file ~/Downloads/nth-term.pdf \
        --title "nth term worksheet" --note "Printable, with space for working"

Use `--unit UNIT` to attach to a whole unit, or `--general` for the Resources
page. `--copy` leaves the original where it is instead of moving it.

For an external link, pass `--url` instead:

    python tools/add_resource.py --unit constructions \
        --title "Compass basics" --url "https://example.org/..." --kind video

If the file is already in the right folder, `--url <bare-filename>` resolves
against that folder. A rooted url (`/maths/...`) is rejected — the build works
out the relative path for each page, so urls are always written
`assets/resources/...`.

Then `python build.py`. `python tools/check_links.py` flags any registered file
that is missing.
