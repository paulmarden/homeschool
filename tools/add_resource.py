#!/usr/bin/env python3
"""Add a resource to data/resources.json without hand-editing JSON.

  python tools/add_resource.py --lesson sequences/finding-the-nth-term \
      --title "nth term worksheet" --url assets/resources/nth-term.pdf \
      --kind worksheet --note "Printable, with space for working"

  python tools/add_resource.py --unit constructions \
      --title "Compass and straight edge basics" \
      --url https://example.org/... --kind video

  python tools/add_resource.py --general --title "..." --url "..."

  python tools/add_resource.py --list
  python tools/add_resource.py --list --lesson sequences/finding-the-nth-term
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRICULUM = os.path.join(ROOT, "data", "curriculum.json")
RESOURCES = os.path.join(ROOT, "data", "resources.json")

KINDS = ("link", "html", "pdf", "video", "worksheet", "sheet", "notebook", "book")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(data):
    with open(RESOURCES, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def known_keys():
    data = load(CURRICULUM)
    units, lessons = set(), set()
    for u in data["units"]:
        units.add(u["slug"])
        for l in u["lessons"]:
            lessons.add("%s/%s" % (u["slug"], l["slug"]))
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
            if where and where not in (scope, key):
                continue
            dump("%s: %s" % (scope[:-1], key), res[scope][key])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    target = ap.add_mutually_exclusive_group()
    target.add_argument("--lesson", metavar="UNIT/LESSON",
                        help="attach to one lesson")
    target.add_argument("--unit", metavar="UNIT", help="attach to a whole unit")
    target.add_argument("--general", action="store_true",
                        help="attach to the Resources page, not a unit or lesson")
    ap.add_argument("--title")
    ap.add_argument("--url", help="an external URL, or a path like "
                                  "assets/resources/thing.pdf")
    ap.add_argument("--kind", choices=KINDS, default=None,
                    help="default: link for a URL, worksheet/pdf inferred from a "
                         "local file extension")
    ap.add_argument("--note", default="")
    ap.add_argument("--group", choices=("links", "ours"), default=None,
                    help="which column it appears in; inferred by default")
    ap.add_argument("--list", action="store_true", help="show what is already there")
    args = ap.parse_args()

    res = load(RESOURCES)

    if args.list:
        where = args.lesson or args.unit or ("general" if args.general else None)
        show(res, where)
        return 0

    if not args.title or not args.url:
        ap.error("--title and --url are required (or use --list)")

    units, lessons = known_keys()
    if args.lesson:
        if args.lesson not in lessons:
            sys.exit("unknown lesson %r -- expected UNIT-SLUG/LESSON-SLUG" % args.lesson)
        bucket = res.setdefault("lessons", {}).setdefault(args.lesson, [])
        where = "lesson %s" % args.lesson
    elif args.unit:
        if args.unit not in units:
            sys.exit("unknown unit %r -- one of: %s"
                     % (args.unit, ", ".join(sorted(units))))
        bucket = res.setdefault("units", {}).setdefault(args.unit, [])
        where = "unit %s" % args.unit
    elif args.general:
        bucket = res.setdefault("general", [])
        where = "general"
    else:
        ap.error("pick a target: --lesson, --unit or --general")

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
        local = os.path.join(ROOT, args.url.replace("/", os.sep))
        if not os.path.exists(local):
            print("note: %s does not exist yet -- drop the file there before "
                  "building" % args.url)

    bucket.append(entry)
    save(res)
    print("added to %s:\n  %s  [%s]\n  %s" % (where, entry["title"], kind, entry["url"]))
    print("\nrun `python build.py` to regenerate the site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
