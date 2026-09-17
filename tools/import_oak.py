"""Import the Oak National Academy Year 8 maths curriculum into curriculum.json.

Deliberately narrow: this keeps the curriculum spine (units, lessons, outcomes,
key learning points, keywords) and the quizzes, and leaves the rest of Oak's
teacher-facing material -- rationale, prior knowledge, misconceptions, teaching
tips -- where it belongs, on Oak's own pages, which every generated page links
to.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

import flight

BASE = "https://www.thenational.academy"
PROGRAMME = "maths-secondary-ks3"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) homeschool-curriculum-import"

UNIT_SLUGS = [
    "estimation-and-rounding",
    "sequences",
    "graphical-representations-of-linear-equations",
    "solving-linear-equations",
    "understanding-multiplicative-relationships-percentages-and-proportionality",
    "graphical-representations-of-data",
    "numerical-summaries-of-data",
    "perimeter-area-and-volume",
    "geometrical-properties-polygons",
    "constructions",
]


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


def scrape_lesson(unit_slug, lesson_slug):
    path = "/teachers/programmes/%s/units/%s/lessons/%s" % (
        PROGRAMME,
        unit_slug,
        lesson_slug,
    )
    html = fetch(path, "lesson__%s__%s" % (unit_slug, lesson_slug))
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
        "contentGuidance": obj.get("contentGuidance"),
        "video": obj.get("videoMuxPlaybackId"),
        "videoSigned": obj.get("videoWithSignLanguageMuxPlaybackId"),
        "oakUrl": BASE + path,
        "starterQuiz": clean_quiz(obj.get("starterQuiz")),
        "exitQuiz": clean_quiz(obj.get("exitQuiz")),
    }


def scrape_unit(index, slug):
    path = "/teachers/programmes/%s/units/%s/lessons" % (PROGRAMME, slug)
    html = fetch(path, "unit__%s" % slug)
    text = flight.flight_text(html)
    # whyThisWhyNow is only a landmark for locating the unit object in the
    # payload -- the field itself is not kept.
    obj, _ = flight.find_object(
        text, "whyThisWhyNow", require=("unitTitle", "lessons"))
    if obj is None:
        raise SystemExit("no unit data for " + slug)
    lessons = []
    for stub in obj.get("lessons") or []:
        lesson = scrape_lesson(slug, stub["lessonSlug"])
        if lesson is None:
            lesson = {
                "slug": stub["lessonSlug"],
                "title": stub.get("lessonTitle"),
                "order": stub.get("orderInUnit"),
                "outcome": stub.get("pupilLessonOutcome") or "",
                "keyLearningPoints": [],
                "keywords": [],
                "equipment": [],
                "starterQuiz": [],
                "exitQuiz": [],
            }
        lessons.append(lesson)
        print("    %2d. %s (%d KLP, %d+%d quiz)" % (
            lesson["order"] or 0,
            lesson["title"],
            len(lesson["keyLearningPoints"]),
            len(lesson["starterQuiz"]),
            len(lesson["exitQuiz"]),
        ), flush=True)
    return {
        "slug": slug,
        "index": index,
        "title": obj.get("unitTitle"),
        "description": obj.get("unitDescription") or "",
        "threads": obj.get("threads") or [],
        "oakUrl": BASE + path,
        "lessons": lessons,
    }


def main():
    units = []
    for i, slug in enumerate(UNIT_SLUGS, 1):
        print("Unit %d: %s" % (i, slug), flush=True)
        units.append(scrape_unit(i, slug))
    data = {
        "subject": "Maths",
        "year": 8,
        "keyStage": "KS3",
        "source": "Oak National Academy",
        "sourceUrl": BASE + "/teachers/programmes/maths-secondary/units?years=8",
        "licence": "Open Government Licence v3.0",
        "units": units,
        "totals": {
            "units": len(units),
            "lessons": sum(len(u["lessons"]) for u in units),
        },
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "curriculum.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("WROTE %s  units=%d lessons=%d" % (
        out, data["totals"]["units"], data["totals"]["lessons"]), flush=True)


if __name__ == "__main__":
    sys.exit(main())
