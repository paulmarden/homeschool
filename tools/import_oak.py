#!/usr/bin/env python3
"""Import an Oak National Academy curriculum into data/curriculum/<subject>.json.

    python tools/import_oak.py --subject maths
    python tools/import_oak.py --all
    python tools/import_oak.py --subject english --year 8

Deliberately narrow: this keeps the curriculum spine (units, lessons, outcomes,
key learning points, keywords) and the quizzes, and leaves the rest of Oak's
teacher-facing material -- rationale, prior knowledge, misconceptions, teaching
tips -- where it belongs, on Oak's own pages, which every generated page links
to.

Units are discovered from the programme's listing page and then confirmed
against each unit's own page, which reports the year it belongs to: the listing
markup carries every unit in the key stage, not just the requested year.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

import flight

BASE = "https://www.thenational.academy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "data", "curriculum")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) homeschool-curriculum-import"

# listing: the page that lists a year's units. programme: the slug the unit and
# lesson pages actually live under -- Oak uses a different one for each.
SUBJECTS = {
    "maths": {
        "title": "Maths",
        "listing": "maths-secondary",
        "programme": "maths-secondary-ks3",
    },
    "english": {
        "title": "English",
        "listing": "english-secondary",
        "programme": "english-secondary-ks3",
    },
}


def fetch(path, key):
    os.makedirs(CACHE, exist_ok=True)
    # Windows MAX_PATH: hash long keys rather than using the slug verbatim.
    name = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
    cached = os.path.join(CACHE, name + ".html")
    if os.path.exists(cached) and os.path.getsize(cached) > 10000:
        with open(cached, encoding="utf-8") as fh:
            return fh.read()
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                html = resp.read().decode("utf-8", "replace")
            break
        except Exception as exc:  # noqa: BLE001 - retry any transport error
            if attempt == 3:
                raise
            print("  retry %s (%s)" % (key, exc), flush=True)
            time.sleep(2 * (attempt + 1))
    with open(cached, "w", encoding="utf-8") as fh:
        fh.write(html)
    time.sleep(0.4)
    return html


def text_parts(parts):
    """Flatten Oak's rich-text arrays ({text,type} / {image_object}) to a string."""
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    out = []
    for p in parts:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            if p.get("type") == "text" and p.get("text"):
                out.append(p["text"])
            elif p.get("type") == "image":
                out.append("[image]")
    return " ".join(out).strip()


def clean_quiz(raw):
    questions = []
    for q in raw or []:
        qtype = q.get("questionType")
        stem = text_parts(q.get("questionStem"))
        images = [
            p.get("imageObject", {}).get("secureUrl")
            for p in (q.get("questionStem") or [])
            if isinstance(p, dict) and p.get("type") == "image"
        ]
        images = [u for u in images if u]
        answers = q.get("answers") or {}
        item = {
            "uid": q.get("questionUid"),
            "type": qtype,
            "stem": stem,
            "images": images,
            "hint": q.get("hint") or "",
            "feedback": q.get("feedback") or "",
        }
        if qtype == "multiple-choice":
            item["options"] = [
                {
                    "text": text_parts(a.get("answer")),
                    "correct": bool(a.get("answerIsCorrect")),
                }
                for a in answers.get("multiple-choice", [])
            ]
        elif qtype == "short-answer":
            item["accept"] = [
                text_parts(a.get("answer")) for a in answers.get("short-answer", [])
            ]
        elif qtype == "order":
            item["order"] = [
                {
                    "text": text_parts(a.get("answer")),
                    "position": a.get("correctOrder"),
                }
                for a in answers.get("order", [])
            ]
        elif qtype == "match":
            item["match"] = [
                {
                    "left": text_parts(a.get("correctChoice")),
                    "right": text_parts(a.get("matchOption")),
                }
                for a in answers.get("match", [])
            ]
        else:
            item["raw"] = answers
        questions.append(item)
    return [q for q in questions if q["stem"]]


def clean_guidance(raw):
    """Oak's content guidance: a list of {label, description, area} dicts."""
    out = []
    for g in raw or []:
        if not isinstance(g, dict):
            if g:
                out.append({"label": str(g), "description": "", "area": ""})
            continue
        label = g.get("contentGuidanceLabel") or ""
        if not label:
            continue
        out.append({
            "label": label,
            "description": g.get("contentGuidanceDescription") or "",
            "area": g.get("contentGuidanceArea") or "",
        })
    return out


def scrape_lesson(programme, unit_slug, lesson_slug):
    path = "/teachers/programmes/%s/units/%s/lessons/%s" % (
        programme, unit_slug, lesson_slug)
    html = fetch(path, "lesson__%s__%s__%s" % (programme, unit_slug, lesson_slug))
    text = flight.flight_text(html)
    obj, _ = flight.find_object(
        text, "keyLearningPoints",
        require=("lessonTitle", "pupilLessonOutcome", "starterQuiz"))
    if obj is None:
        print("  !! no data for %s" % lesson_slug, flush=True)
        return None
    return {
        "slug": lesson_slug,
        "title": obj.get("lessonTitle"),
        "order": obj.get("orderInUnit"),
        "outcome": obj.get("pupilLessonOutcome") or "",
        "keyLearningPoints": [
            k.get("keyLearningPoint")
            for k in obj.get("keyLearningPoints") or []
            if k.get("keyLearningPoint")
        ],
        "keywords": [
            {"word": k.get("keyword"), "definition": k.get("description")}
            for k in obj.get("lessonKeywords") or []
            if k.get("keyword")
        ],
        "equipment": [
            e.get("equipment")
            for e in obj.get("lessonEquipmentAndResources") or []
            if e.get("equipment")
        ],
        "contentGuidance": clean_guidance(obj.get("contentGuidance")),
        "video": obj.get("videoMuxPlaybackId"),
        "videoSigned": obj.get("videoWithSignLanguageMuxPlaybackId"),
        "oakUrl": BASE + path,
        "starterQuiz": clean_quiz(obj.get("starterQuiz")),
        "exitQuiz": clean_quiz(obj.get("exitQuiz")),
    }


def unit_object(programme, slug):
    path = "/teachers/programmes/%s/units/%s/lessons" % (programme, slug)
    html = fetch(path, "unit__%s__%s" % (programme, slug))
    # whyThisWhyNow is only a landmark for locating the unit object in the
    # payload -- the field itself is not kept.
    obj, _ = flight.find_object(
        flight.flight_text(html), "whyThisWhyNow", require=("unitTitle", "lessons"))
    return obj, path


def discover_units(cfg, year):
    """Unit slugs for one year, in teaching order.

    The listing page's markup carries every unit in the key stage, so each
    candidate is confirmed against its own page, which reports its year."""
    listing_path = "/teachers/programmes/%s/units?years=%s" % (cfg["listing"], year)
    html = fetch(listing_path, "listing__%s__%s" % (cfg["listing"], year))
    pat = r"/teachers/programmes/%s/units/([a-z0-9-]+)/lessons" % re.escape(
        cfg["programme"])
    seen, candidates = set(), []
    for slug in re.findall(pat, html):
        if slug not in seen:
            seen.add(slug)
            candidates.append(slug)
    print("  %d candidate units, confirming year..." % len(candidates), flush=True)

    units = []
    for slug in candidates:
        obj, _path = unit_object(cfg["programme"], slug)
        if obj is None:
            print("    ?? no data for %s" % slug, flush=True)
            continue
        if str(obj.get("year")) != str(year):
            continue
        units.append((obj.get("unitIndex") or 0, slug, obj))
    units.sort()
    print("  %d units in year %s" % (len(units), year), flush=True)
    return units


def scrape_unit(cfg, index, slug, obj):
    path = "/teachers/programmes/%s/units/%s/lessons" % (cfg["programme"], slug)
    lessons = []
    for stub in obj.get("lessons") or []:
        lesson = scrape_lesson(cfg["programme"], slug, stub["lessonSlug"])
        if lesson is None:
            lesson = {
                "slug": stub["lessonSlug"],
                "title": stub.get("lessonTitle"),
                "order": stub.get("orderInUnit"),
                "outcome": stub.get("pupilLessonOutcome") or "",
                "keyLearningPoints": [],
                "keywords": [],
                "equipment": [],
                "contentGuidance": [],
                "starterQuiz": [],
                "exitQuiz": [],
            }
        lessons.append(lesson)
        print("    %2d. %s (%d KLP, %d+%d quiz)" % (
            lesson["order"] or 0, lesson["title"],
            len(lesson["keyLearningPoints"]),
            len(lesson["starterQuiz"]), len(lesson["exitQuiz"])), flush=True)
    return {
        "slug": slug,
        "index": index,
        "title": obj.get("unitTitle"),
        "description": obj.get("unitDescription") or "",
        "threads": obj.get("threads") or [],
        "oakUrl": BASE + path,
        "lessons": lessons,
    }


def import_subject(subject, year):
    cfg = SUBJECTS[subject]
    print("== %s, year %s (%s) ==" % (cfg["title"], year, cfg["programme"]), flush=True)
    found = discover_units(cfg, year)
    units = []
    for i, (_idx, slug, obj) in enumerate(found, 1):
        print("Unit %d: %s" % (i, slug), flush=True)
        units.append(scrape_unit(cfg, i, slug, obj))

    data = {
        "subject": cfg["title"],
        "subjectSlug": subject,
        "year": year,
        "keyStage": "KS3",
        "programme": cfg["programme"],
        "source": "Oak National Academy",
        "sourceUrl": "%s/teachers/programmes/%s/units?years=%s"
                     % (BASE, cfg["listing"], year),
        "licence": "Open Government Licence v3.0",
        "units": units,
        "totals": {
            "units": len(units),
            "lessons": sum(len(u["lessons"]) for u in units),
            "questions": sum(len(l["starterQuiz"]) + len(l["exitQuiz"])
                             for u in units for l in u["lessons"]),
        },
    }
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "%s.json" % subject)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("WROTE %s  units=%d lessons=%d questions=%d"
          % (out, data["totals"]["units"], data["totals"]["lessons"],
             data["totals"]["questions"]), flush=True)
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", choices=sorted(SUBJECTS))
    ap.add_argument("--all", action="store_true", help="import every subject")
    ap.add_argument("--year", type=int, default=8)
    args = ap.parse_args()

    if args.all:
        targets = sorted(SUBJECTS)
    elif args.subject:
        targets = [args.subject]
    else:
        ap.error("pass --subject <%s> or --all" % "|".join(sorted(SUBJECTS)))

    for s in targets:
        import_subject(s, args.year)
    return 0


if __name__ == "__main__":
    sys.exit(main())
