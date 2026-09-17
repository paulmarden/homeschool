#!/usr/bin/env python3
"""Optional: download the quiz images so the site works offline.

By default the generated pages hotlink Oak's CDN, which keeps the repo small.
Run this once to vendor the images into assets/quiz-images/ instead; build.py
picks up the manifest automatically on the next build and rewrites the <img>
sources. Delete the directory to go back to hotlinking.
"""
import hashlib
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "curriculum.json")
OUTDIR = os.path.join(ROOT, "assets", "quiz-images")
MANIFEST = os.path.join(OUTDIR, "manifest.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) homeschool-curriculum-import"


def main():
    with open(DATA, encoding="utf-8") as fh:
        data = json.load(fh)

    urls = []
    for unit in data["units"]:
        for lesson in unit["lessons"]:
            for q in lesson["starterQuiz"] + lesson["exitQuiz"]:
                urls.extend(q.get("images") or [])
    urls = list(dict.fromkeys(urls))
    print("%d unique images" % len(urls))

    os.makedirs(OUTDIR, exist_ok=True)
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)

    total = 0
    for i, url in enumerate(urls, 1):
        ext = os.path.splitext(url.split("?")[0])[1].lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
            ext = ".png"
        name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ext
        dest = os.path.join(OUTDIR, name)
        if not os.path.exists(dest):
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    blob = resp.read()
            except Exception as exc:  # noqa: BLE001
                print("  [%d/%d] FAILED %s (%s)" % (i, len(urls), url, exc))
                continue
            with open(dest, "wb") as fh:
                fh.write(blob)
        manifest[url] = name
        total += os.path.getsize(dest)
        if i % 50 == 0 or i == len(urls):
            print("  [%d/%d] %.1f MB" % (i, len(urls), total / 1e6))

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print("vendored %d/%d images, %.1f MB -> %s"
          % (len(manifest), len(urls), total / 1e6, OUTDIR))
    print("run `python build.py` to rebuild against the local copies")


if __name__ == "__main__":
    sys.exit(main())
