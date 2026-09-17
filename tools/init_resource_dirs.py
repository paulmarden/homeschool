#!/usr/bin/env python3
"""Create the resource folder tree: subject / year / unit.

    assets/resources/
      general/
      maths/year-8/estimation-and-rounding/
      maths/year-8/sequences/
      ...

One folder per unit holds the resources for that unit and for every lesson in
it, so a unit's material stays together rather than spreading across 148 lesson
folders. Idempotent -- safe to re-run after adding units or a new subject.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRICULUM = os.path.join(ROOT, "data", "curriculum.json")
RESOURCES_ROOT = os.path.join(ROOT, "assets", "resources")

GITKEEP = (
    "# Keeps this folder in git while it is empty.\n"
    "# Drop resources for this unit here, then register them:\n"
    "#   python tools/add_resource.py --lesson UNIT/LESSON --file <path>\n"
)


def slugify(s):
    return "".join(c if c.isalnum() else "-" for c in str(s).lower()).strip("-")


def subject_dir(data):
    """e.g. maths/year-8 -- relative to assets/resources/."""
    return "%s/year-%s" % (slugify(data["subject"]), data["year"])


def unit_dir(data, unit_slug):
    """Canonical folder for a unit's resources, relative to the repo root."""
    return "assets/resources/%s/%s" % (subject_dir(data), unit_slug)


def general_dir():
    return "assets/resources/general"


def main():
    with open(CURRICULUM, encoding="utf-8") as fh:
        data = json.load(fh)

    wanted = [general_dir()] + [unit_dir(data, u["slug"]) for u in data["units"]]
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

    print("%d folders (%d created):" % (len(wanted), made))
    for rel in wanted:
        n = len([f for f in os.listdir(os.path.join(ROOT, rel.replace("/", os.sep)))
                 if f != ".gitkeep"])
        print("  %-58s %s" % (rel, "%d file(s)" % n if n else "empty"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
