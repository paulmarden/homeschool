#!/usr/bin/env python3
"""Walk every generated page and report broken internal links or assets."""
import os
import re
import sys
from urllib.parse import unquote, urldefrag

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")
REF = re.compile(r'(?:href|src)="([^"]+)"')
IDS = re.compile(r'id="([^"]+)"')


def main():
    pages = []
    for base, _dirs, files in os.walk(SITE):
        for f in files:
            if f.endswith(".html"):
                pages.append(os.path.join(base, f))

    broken = []
    external = set()
    checked = 0
    for page in pages:
        with open(page, encoding="utf-8") as fh:
            body = fh.read()
        anchors = set(IDS.findall(body))
        for ref in REF.findall(body):
            if ref.startswith(("http://", "https://", "mailto:", "data:")):
                external.add(ref.split("?")[0])
                continue
            target, frag = urldefrag(ref)
            if not target:
                if frag and frag not in anchors:
                    broken.append((page, ref, "missing anchor"))
                continue
            checked += 1
            resolved = os.path.normpath(
                os.path.join(os.path.dirname(page), unquote(target)))
            if not os.path.exists(resolved):
                broken.append((page, ref, "missing file"))

    print("pages: %d" % len(pages))
    print("internal refs checked: %d" % checked)
    print("distinct external links: %d" % len(external))
    if broken:
        print("BROKEN: %d" % len(broken))
        for page, ref, why in broken[:40]:
            print("  %s -> %s (%s)" % (os.path.relpath(page, SITE), ref, why))
        return 1
    print("no broken internal links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
