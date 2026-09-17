#!/usr/bin/env python3
"""Add a resource to data/resources.json without hand-editing JSON.

Files live under assets/resources/<subject>/year-<n>/<unit>/, one folder per
unit holding that unit's resources and those of all its lessons. Pass --file
and the file is moved into the right folder for you:

  python tools/add_resource.py --lesson maths/sequences/finding-the-nth-term \
      --file ~/Downloads/nth-term.pdf \
      --title "nth term worksheet" --note "Printable, with space for working"

  python tools/add_resource.py --unit english/gothic-poetry \
      --title "Gothic poetry reading list" \
      --url https://example.org/... --kind link

  python tools/add_resource.py --general --title "..." --url "..."

  python tools/add_resource.py --list
  python tools/add_resource.py --list --unit maths/sequences

Targets are subject-qualified: --unit SUBJECT/UNIT, --lesson SUBJECT/UNIT/LESSON.
--url still works for an external link, or for a file already sitting in the
right folder (a bare filename is resolved against that folder).
"""
import argparse
import glob
import json
import os
import shutil
import sys

import init_resource_dirs as dirs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES = os.path.join(ROOT, "data", "resources.json")

KINDS = ("link", "html", "pdf", "video", "worksheet", "sheet", "notebook", "book")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(data):
    with open(RESOURCES, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def known_keys(curricula):
    """Valid --unit and --lesson targets, subject-qualified."""
    units, lessons = {}, {}
    for slug, data in curricula.items():
        for u in data["units"]:
            units["%s/%s" % (slug, u["slug"])] = (data, u["slug"])
            for l in u["lessons"]:
                lessons["%s/%s/%s" % (slug, u["slug"], l["slug"])] = (data, u["slug"])
    return units, lessons


def show(res, where=None):
    def dump(label, items):
        if not items:
            return
        print("\n%s" % label)
        for r in items:
            print("  - %-52s %s" % (r["title"][:52], r["url"]))

    if where in (None, "general"):
        dump("general", res.get("general") or [])
    for scope in ("units", "lessons"):
        for key in sorted((res.get(scope) or {})):
            if where and where not in (scope, key) and not key.startswith(
                    (where or "") + "/"):
                continue
            dump("%s: %s" % (scope[:-1], key), res[scope][key])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    target = ap.add_mutually_exclusive_group()
    target.add_argument("--lesson", metavar="SUBJECT/UNIT/LESSON",
                        help="attach to one lesson")
    target.add_argument("--unit", metavar="SUBJECT/UNIT",
                        help="attach to a whole unit")
    target.add_argument("--general", action="store_true",
                        help="attach to the Resources page, not a unit or lesson")
    ap.add_argument("--title")
    ap.add_argument("--url", help="an external URL, or a path under "
                                  "assets/resources/ (a bare filename is "
                                  "resolved against this target's folder)")
    ap.add_argument("--file", help="a file to move into this target's resource "
                                   "folder and register")
    ap.add_argument("--copy", action="store_true",
                    help="with --file, copy instead of moving")
    ap.add_argument("--kind", choices=KINDS, default=None,
                    help="default: link for a URL, inferred from a local file's "
                         "extension otherwise")
    ap.add_argument("--note", default="")
    ap.add_argument("--group", choices=("links", "ours"), default=None,
                    help="which column it appears in; inferred by default")
    ap.add_argument("--list", action="store_true", help="show what is already there")
    args = ap.parse_args()

    res = load(RESOURCES)
    curricula = dirs.load_curricula()

    if args.list:
        where = args.lesson or args.unit or ("general" if args.general else None)
        show(res, where)
        return 0

    if not args.title or not (args.url or args.file):
        ap.error("--title and one of --url / --file are required (or use --list)")
    if args.url and args.file:
        ap.error("pass --url or --file, not both")

    units, lessons = known_keys(curricula)
    if args.lesson:
        if args.lesson not in lessons:
            sys.exit("unknown lesson %r -- expected SUBJECT/UNIT/LESSON, subject "
                     "one of: %s" % (args.lesson, ", ".join(sorted(curricula))))
        data, unit_slug = lessons[args.lesson]
        bucket = res.setdefault("lessons", {}).setdefault(args.lesson, [])
        where = "lesson %s" % args.lesson
        folder = dirs.unit_dir(data, unit_slug)
    elif args.unit:
        if args.unit not in units:
            sys.exit("unknown unit %r -- expected SUBJECT/UNIT, subject one of: %s"
                     % (args.unit, ", ".join(sorted(curricula))))
        data, unit_slug = units[args.unit]
        bucket = res.setdefault("units", {}).setdefault(args.unit, [])
        where = "unit %s" % args.unit
        folder = dirs.unit_dir(data, unit_slug)
    elif args.general:
        bucket = res.setdefault("general", [])
        where = "general"
        folder = dirs.general_dir()
    else:
        ap.error("pick a target: --lesson, --unit or --general")

    # --file: put it in this target's folder and use that as the url.
    if args.file:
        src = os.path.abspath(os.path.expanduser(args.file))
        if not os.path.isfile(src):
            sys.exit("no such file: %s" % args.file)
        dest_dir = os.path.join(ROOT, folder.replace("/", os.sep))
        os.makedirs(dest_dir, exist_ok=True)
        name = os.path.basename(src)
        dest = os.path.join(dest_dir, name)
        if os.path.exists(dest) and not os.path.samefile(src, dest):
            sys.exit("%s/%s already exists -- rename it or remove the old one"
                     % (folder, name))
        if not os.path.exists(dest):
            (shutil.copy2 if args.copy else shutil.move)(src, dest)
            print("%s %s -> %s/" % ("copied" if args.copy else "moved", name, folder))
        keep = os.path.join(dest_dir, ".gitkeep")
        if os.path.exists(keep):
            os.remove(keep)
        args.url = "%s/%s" % (folder, name)
    elif "://" not in args.url and "/" not in args.url:
        # a bare filename belongs in this target's folder
        args.url = "%s/%s" % (folder, args.url)

    external = "://" in args.url
    kind = args.kind
    if not kind:
        ext = os.path.splitext(args.url.split("?")[0])[1].lower()
        kind = {".pdf": "pdf", ".html": "html", ".htm": "html",
                ".md": "notebook", ".ipynb": "notebook",
                ".csv": "sheet", ".xlsx": "sheet",
                ".mp4": "video", ".mov": "video"}.get(ext, "link" if external else "pdf")

    entry = {"title": args.title, "url": args.url, "kind": kind}
    if args.note:
        entry["note"] = args.note
    if args.group:
        entry["group"] = args.group

    if any(r["url"] == entry["url"] for r in bucket):
        sys.exit("that url is already on %s" % where)

    if not external:
        if args.url.startswith("/"):
            sys.exit("a rooted url (%s) cannot be resolved -- write it relative, "
                     "as %s/<file>" % (args.url, folder))
        local = os.path.join(ROOT, args.url.replace("/", os.sep))
        if not os.path.exists(local):
            print("note: %s does not exist yet -- drop the file there before "
                  "building" % args.url)
        elif not args.url.startswith(folder + "/"):
            print("note: %s sits outside this target's folder (%s/). It will "
                  "still work, but resources are easier to find when they live "
                  "with their unit." % (args.url, folder))

    bucket.append(entry)
    save(res)
    print("added to %s:\n  %s  [%s]\n  %s" % (where, entry["title"], kind, entry["url"]))
    print("\nrun `python build.py` to regenerate the site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
