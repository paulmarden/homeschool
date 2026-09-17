#!/usr/bin/env python3
"""Create the resource folder tree: subject / year / unit.

    assets/resources/
      general/
      maths/year-8/estimation-and-rounding/
      english/year-8/a-midsummer-nights-dream/
      ...

One folder per unit holds the resources for that unit and for every lesson in
it, so a unit's material stays together rather than spreading across hundreds
of lesson folders. Idempotent -- safe to re-run after adding units, a year or
a subject.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRICULUM_DIR = os.path.join(ROOT, "data", "curriculum")
RESOURCES_ROOT = os.path.join(ROOT, "assets", "resources")

GITKEEP = (
    "# Keeps this folder in git while it is empty.\n"
    "# Drop resources for this unit here, then register them:\n"
    "#   python tools/add_resource.py --lesson SUBJECT/UNIT/LESSON --file <path>\n"
)


def load_curricula():
    out = {}
    for path in sorted(glob.glob(os.path.join(CURRICULUM_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        slug = data.get("subjectSlug") or os.path.splitext(os.path.basename(path))[0]
        out[slug] = data
    return out


def subject_dir(data):
    """e.g. maths/year-8 -- relative to assets/resources/."""
    return "%s/year-%s" % (data["subjectSlug"], data["year"])


def unit_dir(data, unit_slug):
    """Canonical folder for a unit's resources, relative to the repo root."""
    return "assets/resources/%s/%s" % (subject_dir(data), unit_slug)


def general_dir():
    return "assets/resources/general"


def main():
    curricula = load_curricula()
    if not curricula:
        sys.exit("no curriculum files in %s" % CURRICULUM_DIR)

    wanted = [general_dir()]
    for slug in sorted(curricula):
        data = curricula[slug]
        wanted += [unit_dir(data, u["slug"]) for u in data["units"]]

    made = 0
    for rel in wanted:
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.isdir(path):
            os.makedirs(path)
            made += 1
        keep = os.path.join(path, ".gitkeep")
        if not os.listdir(path):
            with open(keep, "w", encoding="utf-8") as fh:
                fh.write(GITKEEP)
        elif os.path.exists(keep) and len(os.listdir(path)) > 1:
            os.remove(keep)  # folder has real content now

    print("%d folders (%d created)" % (len(wanted), made))
    for rel in wanted:
        files = [f for f in os.listdir(os.path.join(ROOT, rel.replace("/", os.sep)))
                 if f != ".gitkeep"]
        if files:
            print("  %-62s %d file(s)" % (rel, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
