#!/usr/bin/env python3
"""Generate the Year 8 Study Hub static site from data/curriculum.json.

Plain HTML on the Modernist stylesheet -- no framework, no build toolchain.
Run `python build.py` and open site/index.html.
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "curriculum.json")
RESOURCE_DATA = os.path.join(ROOT, "data", "resources.json")
OUT = os.path.join(ROOT, "site")
ASSETS = os.path.join(ROOT, "assets")
IMAGE_MANIFEST = os.path.join(ASSETS, "quiz-images", "manifest.json")

# Populated when tools/fetch_images.py has vendored the quiz images; otherwise
# the pages hotlink Oak's CDN.
LOCAL_IMAGES = {}

# Our own resources, loaded from data/resources.json in main().
RESOURCES = {}

SITE_NAME = "Year 8 Study Hub"

# The wireframe's subject grid. Only maths is built out so far; the rest are
# shown as placeholders rather than dead links.
SUBJECTS = [
    {"n": "01", "title": "English", "ready": False},
    {"n": "02", "title": "Maths", "ready": True, "href": "maths/"},
    {"n": "03", "title": "Science", "ready": False},
    {"n": "04", "title": "Art", "ready": False},
    {"n": "05", "title": "Geography", "ready": False},
    {"n": "06", "title": "History", "ready": False},
]

BLANK = re.compile(r"\{\{\s*\}\}")


def image_src(url, depth):
    name = LOCAL_IMAGES.get(url)
    if name:
        return "%sassets/quiz-images/%s" % (up(depth), name)
    return url


def esc(s):
    return html.escape(s or "", quote=True)


def stem_html(text):
    """Oak marks short-answer gaps with `{{ }}`; draw them as a rule."""
    return BLANK.sub('<span class="blank"></span>', esc(text))


def up(depth):
    return "../" * depth if depth else ""


def icon_close():
    # Lucide `x`
    return (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>'
    )


def icon_external():
    # Lucide `external-link`
    return (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>'
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>'
    )


def oak_button(url, label="View on Oak Academy"):
    return (
        '<a class="btn btn-secondary" href="%s" target="_blank" rel="noopener">'
        '%s%s</a>' % (esc(url), esc(label), icon_external())
    )


def nav(depth, current):
    def link(href, label, key):
        cur = ' aria-current="page"' if key == current else ""
        return '<a href="%s%s"%s>%s</a>' % (up(depth), href, cur, label)

    return (
        '<nav class="nav">'
        '<div class="nav-brand"><a href="%sindex.html">%s</a></div>'
        '%s%s%s%s</nav>'
        % (up(depth), SITE_NAME,
           link("index.html", "Subjects", "home"),
           link("maths/index.html", "Maths", "maths"),
           link("resources.html", "Resources", "resources"),
           link("about.html", "About", "about"))
    )


def crumb(depth, parts):
    """parts: list of (label, href-or-None); the last is the current page."""
    bits = []
    for label, href in parts:
        if href:
            bits.append('<a href="%s%s">%s</a>' % (up(depth), href, esc(label)))
        else:
            bits.append(esc(label))
    return '<div class="crumb">%s</div>' % " / ".join(bits)


def footer(depth):
    return (
        '<footer class="foot">'
        '<p>Curriculum content &mdash; unit and lesson titles, learning outcomes, '
        'key learning points, keywords and quiz questions &mdash; is '
        'from <a href="https://www.thenational.academy/" target="_blank" rel="noopener">'
        'Oak National Academy</a>, used under the '
        '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" '
        'target="_blank" rel="noopener">Open Government Licence v3.0</a>. '
        'Every unit and lesson links back to its source. '
        '<a href="%sabout.html">More about this site</a>.</p>'
        '</footer>' % up(depth)
    )


def page(depth, title, body, current="", description="", scripts=()):
    head_scripts = "".join(
        '<script src="%s%s" defer></script>' % (up(depth), s) for s in scripts)
    return (
        '<!DOCTYPE html>\n<html lang="en-GB">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>%s</title>\n'
        '<meta name="description" content="%s">\n'
        '<link rel="stylesheet" href="%sassets/ds/styles.css">\n'
        '<link rel="stylesheet" href="%sassets/site.css">\n'
        '%s</head>\n<body>\n<div class="page">\n%s\n%s\n%s</div>\n</body>\n</html>\n'
        % (esc(title), esc(description), up(depth), up(depth), head_scripts,
           nav(depth, current), body, footer(depth))
    )


def write(relpath, content):
    path = os.path.join(OUT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


# ── quiz rendering ────────────────────────────────────────────────────────────

def render_question(q, idx, depth=3):
    """Static, answerable-on-paper markup. quiz.js layers live marking on top."""
    parts = ['<div class="q" data-qtype="%s">' % esc(q["type"])]
    parts.append('<div class="qstem"><span class="qnum">%d</span>'
                 '<span>%s</span></div>' % (idx, stem_html(q["stem"])))
    for src in q.get("images") or []:
        parts.append('<div class="qimg"><img src="%s" alt="" loading="lazy"></div>'
                     % esc(image_src(src, depth)))

    qtype = q["type"]
    answer_text = ""

    if qtype == "multiple-choice":
        opts = q.get("options") or []
        multi = sum(1 for o in opts if o["correct"]) > 1
        kind = "checkbox" if multi else "radio"
        parts.append('<div class="opts" role="group">')
        for oi, o in enumerate(opts):
            parts.append(
                '<label class="opt" data-correct="%s">'
                '<input type="%s" name="q%d_%s" value="%d">'
                '<span class="box"></span><span class="txt">%s</span></label>'
                % ("1" if o["correct"] else "0", kind, idx, id(q) % 99991, oi,
                   esc(o["text"])))
        parts.append('</div>')
        if multi:
            parts.append('<p class="rd">Select all that apply.</p>')
        answer_text = "; ".join(esc(o["text"]) for o in opts if o["correct"])

    elif qtype == "short-answer":
        accept = q.get("accept") or []
        parts.append(
            '<div class="qrow"><input class="input" type="text" '
            'autocomplete="off" spellcheck="false" placeholder="Your answer" '
            'data-accept="%s"></div>'
            % esc(json.dumps(accept, ensure_ascii=False)))
        answer_text = " / ".join(esc(a) for a in accept)

    elif qtype == "order":
        items = sorted(q.get("order") or [], key=lambda x: (x["position"] or 0))
        shown = sorted(q.get("order") or [], key=lambda x: esc(x["text"]))
        n = len(items)
        parts.append('<div class="ordr">')
        for it in shown:
            opts = "".join('<option value="%d">%d</option>' % (k, k)
                           for k in range(1, n + 1))
            parts.append(
                '<div class="matchrow"><span class="ml">%s</span>'
                '<select class="input" data-position="%s">'
                '<option value="">Position…</option>%s</select></div>'
                % (esc(it["text"]), esc(str(it["position"])), opts))
        parts.append('</div>')
        answer_text = " &rarr; ".join(esc(i["text"]) for i in items)

    elif qtype == "match":
        pairs = q.get("match") or []
        choices = sorted({p["left"] for p in pairs})
        parts.append('<div class="mtch">')
        for p in pairs:
            opts = "".join('<option value="%s">%s</option>' % (esc(c), esc(c))
                           for c in choices)
            parts.append(
                '<div class="matchrow"><span class="ml">%s</span>'
                '<select class="input" data-answer="%s">'
                '<option value="">Choose…</option>%s</select></div>'
                % (esc(p["right"]), esc(p["left"]), opts))
        parts.append('</div>')
        answer_text = "; ".join("%s &rarr; %s" % (esc(p["right"]), esc(p["left"]))
                                for p in pairs)

    if q.get("hint"):
        parts.append('<details class="qhint"><summary>Hint</summary>'
                     '<div class="rd">%s</div></details>' % stem_html(q["hint"]))

    parts.append('<details class="qhint qanswer"><summary>Show answer</summary>'
                 '<div class="qfeedback"><span class="lbl">Answer</span>%s</div>'
                 % (answer_text or "&mdash;"))
    if q.get("feedback"):
        parts.append('<div class="qfeedback"><span class="lbl">Why</span>%s</div>'
                     % stem_html(q["feedback"]))
    parts.append('</details>')

    parts.append('</div>')
    return "".join(parts)


def render_quiz(title, questions, quiz_id, lesson_key):
    """A quiz lives in a <dialog>; the page shows only a button that opens it."""
    if not questions:
        return "", ""
    qs = "".join(render_question(q, i + 1) for i, q in enumerate(questions))
    dialog = (
        '<dialog class="qdialog" id="%s-dialog" data-quiz="%s" '
        'data-lesson="%s" data-total="%d">'
        '<div class="qdialog-head">'
        '<div><h2 class="quiztitle">%s</h2>'
        '<span class="quizscore" data-score>%d questions</span></div>'
        '<button type="button" class="btn btn-icon btn-secondary" data-close '
        'aria-label="Close quiz">%s</button>'
        '</div>'
        '<div class="qdialog-body">%s</div>'
        '<div class="qdialog-foot qactions">'
        '<button type="button" class="btn btn-primary" data-check>Check answers</button>'
        '<button type="button" class="btn btn-secondary" data-reveal>Reveal all answers</button>'
        '<button type="button" class="btn btn-secondary" data-reset>Clear</button>'
        '<button type="button" class="btn btn-secondary" data-close>Close</button>'
        '</div></dialog>'
        % (esc(quiz_id), esc(quiz_id), esc(lesson_key), len(questions),
           esc(title), len(questions), icon_close(), qs)
    )
    button = (
        '<button type="button" class="btn btn-primary quizbtn" '
        'data-open="%s-dialog">%s<span class="quizbtn-meta">%d questions</span>'
        '</button>' % (esc(quiz_id), esc(title), len(questions))
    )
    return button, dialog


# ── resources ─────────────────────────────────────────────────────────────────

KIND_TAGS = {
    "html": ("HTML", "tag-accent"),
    "pdf": ("PDF", "tag-neutral"),
    "video": ("Video", "tag-neutral"),
    "worksheet": ("Worksheet", "tag-neutral"),
    "sheet": ("Sheet", "tag-neutral"),
    "notebook": ("Notes", "tag-neutral"),
    "book": ("Book", "tag-neutral"),
    "link": ("External", "tag-outline"),
}


def resource_group(r):
    if r.get("group"):
        return r["group"]
    return "links" if "://" in r.get("url", "") else "ours"


def resource_row(r, depth):
    url = r.get("url", "")
    external = "://" in url
    href = url if external else up(depth) + url
    label, cls = KIND_TAGS.get(r.get("kind", "link"), KIND_TAGS["link"])
    if external:
        where = url.split("://", 1)[1].split("/")[0].replace("www.", "")
    else:
        where = url.rsplit("/", 1)[-1]
    note = r.get("note") or where
    target = ' target="_blank" rel="noopener"' if external else ""
    return (
        '<a class="resrow" href="%s"%s>'
        '<span><span class="rt">%s</span>'
        '<span class="rd">%s</span></span>'
        '<span class="tag %s">%s</span></a>'
        % (esc(href), target, esc(r.get("title", url)), esc(note), cls, esc(label))
    )


def resource_columns(items, depth, empty_hint=""):
    """The wireframe's two columns: references we use, and things we keep."""
    links = [r for r in items if resource_group(r) == "links"]
    ours = [r for r in items if resource_group(r) == "ours"]

    def col(title, rows, hint):
        if rows:
            body = "".join(resource_row(r, depth) for r in rows)
        else:
            body = '<p class="rd resempty">%s</p>' % hint
        return '<div class="col"><div class="coltitle">%s</div>%s</div>' % (title, body)

    # Ours leads: what we keep is the point of the site, references are backup.
    return (
        '<div class="cols">%s%s</div>'
        % (col("Our resources", ours,
               empty_hint or "Nothing here yet."),
           col("Relevant links", links,
               empty_hint or "Nothing here yet."))
    )


def resources_for(res, scope, key):
    if scope == "general":
        return res.get("general") or []
    return (res.get(scope) or {}).get(key) or []


def add_hint(flag, key):
    return ('Nothing here yet &mdash; add one with '
            '<code>python tools/add_resource.py %s %s --title "…" --url "…"</code>'
            % (flag, esc(key)))


# ── pages ─────────────────────────────────────────────────────────────────────

def build_home(data):
    units = data["units"]
    lessons = data["totals"]["lessons"]
    questions = sum(len(l["starterQuiz"]) + len(l["exitQuiz"])
                    for u in units for l in u["lessons"])

    cards = []
    for s in SUBJECTS:
        if s["ready"]:
            cards.append(
                '<a class="card" href="%s"><div class="card-kicker">%s</div>'
                '<div class="card-title">%s</div>'
                '<div class="card-meta">%d units &middot; %d lessons</div></a>'
                % (esc(s["href"]), esc(s["n"]), esc(s["title"]), len(units), lessons))
        else:
            cards.append(
                '<div class="card is-pending"><div class="card-kicker">%s</div>'
                '<div class="card-title">%s</div>'
                '<div class="card-meta">Not yet added</div></div>'
                % (esc(s["n"]), esc(s["title"])))

    body = (
        '<div class="wrap">'
        '<p class="kicker">Homeschool companion</p>'
        '<h1 style="max-width:820px;font-size:48px;">Resources built alongside the '
        'Oak Academy Year 8 curriculum.</h1>'
        '<p class="lede" style="font-size:16px;">Every unit and lesson links back to '
        'the matching Oak Academy lesson, with the learning points, keywords, '
        'points, keywords and quizzes, alongside the resources we keep.</p>'
        '<div class="factrow">'
        '<div class="fact"><div class="n">%d</div><div class="l">Units</div></div>'
        '<div class="fact"><div class="n">%d</div><div class="l">Lessons</div></div>'
        '<div class="fact"><div class="n">%s</div><div class="l">Quiz questions</div></div>'
        '</div>'
        '<div class="hr" style="margin-bottom:40px;"></div>'
        '<h2 class="sectiontitle">Subjects &mdash; Year 8</h2>'
        '<div class="grid6">%s</div>'
        '</div>'
        % (len(units), lessons, "{:,}".format(questions), "".join(cards))
    )
    write("index.html", page(
        0, "%s — Year 8 homeschool resources" % SITE_NAME, body, current="home",
        description="Year 8 homeschool study hub built alongside the Oak National "
                    "Academy curriculum."))


def build_subject(data):
    units = data["units"]
    cards = []
    for u in units:
        n_res = len(resources_for(RESOURCES, "units", u["slug"])) + sum(
            len(resources_for(RESOURCES, "lessons", "%s/%s" % (u["slug"], l["slug"])))
            for l in u["lessons"])
        res_meta = (' &middot; <span class="resct">%d resource%s</span>'
                    % (n_res, "" if n_res == 1 else "s")) if n_res else ""
        cards.append(
            '<a class="card" href="%s/index.html">'
            '<div class="card-kicker">Unit %d</div>'
            '<div class="card-title">%s</div>'
            '<div class="card-body">%s</div>'
            '<div class="card-meta">%d lessons%s'
            '<span data-unit="%s" data-unit-prog hidden></span></div></a>'
            % (esc(u["slug"]), u["index"], esc(u["title"]),
               esc(u["description"]), len(u["lessons"]), res_meta, esc(u["slug"])))

    body = (
        crumb(1, [("Home", "index.html"), ("Maths", None), ("Year 8", None)])
        + '<div class="wrap">'
        '<div class="pagehead"><h1>Maths &mdash; Year 8</h1>%s</div>'
        '<p class="lede">Units run in Oak Academy\'s Year 8 sequence. '
        '%d units, %d lessons.</p>'
        '<div class="unitlist">%s</div>'
        '</div>'
        % (oak_button(data["sourceUrl"], "View on Oak Academy"),
           len(units), data["totals"]["lessons"], "".join(cards))
    )
    write("maths/index.html", page(
        1, "Maths — Year 8 | %s" % SITE_NAME, body, current="maths",
        description="All 10 Year 8 maths units from the Oak National Academy "
                    "curriculum.", scripts=("assets/progress.js",)))


def build_resources(data):
    """One page listing everything we keep, so it is all reachable from one place."""
    total = 0
    sections = []

    general = resources_for(RESOURCES, "general", None)
    total += len(general)
    sections.append(
        '<h2 class="sectiontitle" style="margin:0 0 0;">General</h2>'
        + resource_columns(general, 0, add_hint("--general", "").replace(
            ' </code>', '</code>')))

    for u in data["units"]:
        unit_items = resources_for(RESOURCES, "units", u["slug"])
        rows = []
        for r in unit_items:
            rows.append(resource_row(r, 0))
        for l in u["lessons"]:
            key = "%s/%s" % (u["slug"], l["slug"])
            for r in resources_for(RESOURCES, "lessons", key):
                rows.append(
                    '<div class="resgroup"><a class="resfrom" href="maths/%s/%s/'
                    'index.html">Lesson %d &mdash; %s</a>%s</div>'
                    % (esc(u["slug"]), esc(l["slug"]), l["order"] or 0,
                       esc(l["title"]), resource_row(r, 0)))
        if not rows:
            continue
        total += len(rows)
        sections.append(
            '<h2 class="sectiontitle" style="margin:48px 0 0;">'
            '<a href="maths/%s/index.html">Unit %d &mdash; %s</a></h2>'
            '<div class="cols cols-1"><div class="col">%s</div></div>'
            % (esc(u["slug"]), u["index"], esc(u["title"]), "".join(rows)))

    body = (
        crumb(0, [("Home", "index.html"), ("Resources", None)])
        + '<div class="wrap">'
        '<div class="pagehead"><h1>Resources</h1></div>'
        '<p class="lede">Everything we keep, in one place. %d item%s. '
        'Anything attached to a unit or a lesson also shows up on that page.</p>'
        '%s'
        '<div class="cols cols-1" style="margin-top:48px;"><div class="col">'
        '<div class="coltitle">Adding a resource</div>'
        '<p class="rd" style="font-size:14px;">Drop files in '
        '<code>assets/resources/</code> and register them, or point at a URL:</p>'
        '<pre class="cmd">python tools/add_resource.py --lesson UNIT/LESSON \\\n'
        '    --title "Title" --url assets/resources/thing.pdf --kind worksheet\n\n'
        'python tools/add_resource.py --unit UNIT --title "…" --url "https://…"\n'
        'python tools/add_resource.py --general --title "…" --url "https://…"\n\n'
        'python build.py</pre>'
        '<p class="rd" style="font-size:14px;">Or edit '
        '<code>data/resources.json</code> directly &mdash; it is the source of '
        'truth and lives in git, so resources are shared across every machine '
        'that clones the repo.</p>'
        '</div></div>'
        '</div>'
        % (total, "" if total == 1 else "s", "".join(sections))
    )
    write("resources.html", page(
        0, "Resources | %s" % SITE_NAME, body, current="resources",
        description="Links, worksheets and notes we keep for Year 8."))


def build_unit(data, u):
    rows = []
    for l in u["lessons"]:
        key = "%s/%s" % (u["slug"], l["slug"])
        n_res = len(resources_for(RESOURCES, "lessons", key))
        badges = ""
        if n_res:
            badges = ('<span class="tag tag-accent">%d resource%s</span>'
                      % (n_res, "" if n_res == 1 else "s"))
        rows.append(
            '<a class="modrow" href="%s/index.html" data-lesson="%s">'
            '<span class="modnum">%02d</span>'
            '<span><span class="mt">%s</span><br><span class="mm">%s</span></span>'
            '<span class="rowtags">%s<span class="tag tag-neutral" '
            'data-lesson-score hidden></span></span></a>'
            % (esc(l["slug"]), esc(key), l["order"] or 0, esc(l["title"]),
               esc(l["outcome"]), badges))

    side = []
    if u["whyThisWhyNow"]:
        side.append('<div class="col"><div class="coltitle">Why this, why now</div>'
                    '<p class="rd" style="font-size:14px;">%s</p></div>'
                    % esc(u["whyThisWhyNow"]))
    if u["priorKnowledge"]:
        items = "".join('<div class="resrow"><div class="rt">%s</div></div>' % esc(p)
                        for p in u["priorKnowledge"])
        side.append('<div class="col"><div class="coltitle">Prior knowledge</div>%s</div>'
                    % items)
    context = '<div class="cols">%s</div>' % "".join(side) if side else ""

    threads = ""
    if u["threads"]:
        threads = " ".join('<span class="tag tag-accent">%s</span>' % esc(t)
                           for t in u["threads"])

    body = (
        crumb(2, [("Home", "index.html"), ("Maths", "maths/index.html"),
                  ("Year 8", "maths/index.html"), (u["title"], None)])
        + '<div class="wrap">'
        '<p class="kicker">Unit %d of %d</p>'
        '<div class="pagehead"><h1>%s</h1>%s</div>'
        '<p class="lede">%s</p>'
        '%s'
        '%s'
        '<h2 class="sectiontitle" style="margin:48px 0 0;">Unit resources</h2>'
        '%s'
        '<div class="lessonshead">'
        '<h2 class="sectiontitle" style="margin:48px 0 0;">%d lessons</h2>'
        '<span class="unitprog" data-unit="%s" hidden></span></div>'
        '<div class="hr" style="margin:12px 0 8px;"></div>'
        '%s'
        '</div>'
        % (u["index"], len(data["units"]), esc(u["title"]), oak_button(u["oakUrl"]),
           esc(u["description"]),
           ('<p style="margin:-24px 0 32px;">%s</p>' % threads) if threads else "",
           context,
           resource_columns(resources_for(RESOURCES, "units", u["slug"]), 2,
                            add_hint("--unit", u["slug"])),
           len(u["lessons"]), esc(u["slug"]), "".join(rows))
    )
    write("maths/%s/index.html" % u["slug"], page(
        2, "%s | Maths Year 8 | %s" % (u["title"], SITE_NAME), body, current="maths",
        description=u["description"], scripts=("assets/progress.js",)))


def build_lesson(data, u, l, prev_l, next_l):
    cols = []
    if l["keyLearningPoints"]:
        items = "".join("<li>%s</li>" % esc(k) for k in l["keyLearningPoints"])
        cols.append('<div class="col"><div class="coltitle">Key learning points</div>'
                    '<ol class="numlist">%s</ol></div>' % items)
    if l["keywords"]:
        rows = "".join(
            '<div class="resrow"><div><div class="rt">%s</div>'
            '<div class="rd">%s</div></div></div>'
            % (esc(k["word"]), esc(k["definition"])) for k in l["keywords"])
        cols.append('<div class="col"><div class="coltitle">Keywords</div>%s</div>' % rows)
    block1 = ('<div class="cols%s">%s</div>'
              % ("" if len(cols) == 2 else " cols-1", "".join(cols))) if cols else ""

    lesson_key = "%s/%s" % (u["slug"], l["slug"])

    equipment = ""
    if l.get("equipment"):
        rows = "".join('<div class="resrow"><span class="rt">%s</span></div>' % esc(e)
                       for e in l["equipment"])
        equipment = ('<div class="cols cols-1"><div class="col">'
                     '<div class="coltitle">Equipment</div>%s</div></div>' % rows)

    # The reason the site exists: what we keep for this lesson.
    items = resources_for(RESOURCES, "lessons", lesson_key)
    resources = (
        '<h2 class="sectiontitle" style="margin:48px 0 0;">Resources</h2>'
        + resource_columns(items, 3, add_hint("--lesson", lesson_key))
    )

    starter_btn, starter_dlg = render_quiz(
        "Starter quiz", l["starterQuiz"], "starter", lesson_key)
    exit_btn, exit_dlg = render_quiz(
        "Exit quiz", l["exitQuiz"], "exit", lesson_key)
    quizzes = ""
    if starter_btn or exit_btn:
        quizzes = (
            '<h2 class="sectiontitle" style="margin:48px 0 0;">Quizzes</h2>'
            '<div class="cols cols-1"><div class="col">'
            '<div class="quizlaunch" data-lesson="%s">%s%s</div>'
            '<p class="quizstate" data-lesson-state hidden></p>'
            '</div></div>%s%s'
            % (esc(lesson_key), starter_btn, exit_btn, starter_dlg, exit_dlg))

    def pager_cell(lesson, side, label):
        if not lesson:
            return ('<span class="%s"><span class="lbl">%s</span>'
                    '<span class="ttl text-muted">&mdash;</span></span>' % (side, label))
        return ('<a class="%s" href="../%s/index.html"><span class="lbl">%s</span>'
                '<span class="ttl">%s</span></a>'
                % (side, esc(lesson["slug"]), label, esc(lesson["title"])))

    pager = ('<div class="pager">%s%s</div>'
             % (pager_cell(prev_l, "prev", "Previous lesson"),
                pager_cell(next_l, "next", "Next lesson")))

    guidance = ""
    if l.get("contentGuidance"):
        cg = l["contentGuidance"]
        if isinstance(cg, list):
            cg = "; ".join(str(c) for c in cg)
        guidance = ('<p><span class="tag tag-outline">Content guidance</span> '
                    '<span class="rd">%s</span></p>' % esc(str(cg)))

    body = (
        crumb(3, [("Home", "index.html"), ("Maths", "maths/index.html"),
                  ("Year 8", "maths/index.html"),
                  (u["title"], "maths/%s/index.html" % u["slug"]),
                  (l["title"], None)])
        + '<div class="wrap">'
        '<div class="pagehead"><div>'
        '<div class="tag tag-accent" style="margin-bottom:12px;">Lesson %d of %d</div>'
        '<h1>%s</h1></div>%s</div>'
        '<p class="lede" style="margin-bottom:0;">%s</p>'
        '%s%s%s%s%s%s'
        '</div>'
        % (l["order"] or 0, len(u["lessons"]), esc(l["title"]),
           oak_button(l["oakUrl"]), esc(l["outcome"]), guidance,
           block1, equipment, resources, quizzes, pager)
    )
    write("maths/%s/%s/index.html" % (u["slug"], l["slug"]), page(
        3, "%s | %s | %s" % (l["title"], u["title"], SITE_NAME), body,
        current="maths", description=l["outcome"],
        scripts=("assets/progress.js", "assets/quiz.js")))


def build_about(data):
    body = (
        crumb(0, [("Home", "index.html"), ("About", None)])
        + '<div class="wrap">'
        '<h1>About this site</h1>'
        '<p class="lede">A homeschool study hub for Year 8, built directly on the '
        'Oak National Academy curriculum sequence.</p>'
        '<div class="cols">'
        '<div class="col"><div class="coltitle">What is here</div>'
        '<div class="resrow"><div><div class="rt">%d units, %d lessons</div>'
        '<div class="rd">The complete Oak National Academy Year 8 maths programme, '
        'in teaching order.</div></div></div>'
        '<div class="resrow"><div><div class="rt">Learning points and keywords</div>'
        '<div class="rd">Each lesson carries its pupil outcome, key learning points '
        'and keyword definitions.</div></div></div>'
        '<div class="resrow"><div><div class="rt">Our resources</div>'
        '<div class="rd">Links, worksheets and notes we keep, attached to the unit '
        'or lesson they belong to.</div></div></div>'
        '<div class="resrow"><div><div class="rt">%s quiz questions</div>'
        '<div class="rd">Every starter and exit quiz, answerable in the browser with '
        'hints, marking and feedback.</div></div></div>'
        '</div>'
        '<div class="col"><div class="coltitle">Source and licence</div>'
        '<p class="rd" style="font-size:14px;">Curriculum content is from '
        '<a href="https://www.thenational.academy/" target="_blank" rel="noopener">'
        'Oak National Academy</a> and is used under the '
        '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" '
        'target="_blank" rel="noopener">Open Government Licence v3.0</a>.</p>'
        '<p class="rd" style="font-size:14px;">This site is not affiliated with or '
        'endorsed by Oak National Academy. Every unit and lesson page links back to '
        'its source page so you can use the original videos, slides and worksheets, '
        'which are not reproduced here.</p>'
        '<p class="rd" style="font-size:14px;">Content was captured from the '
        "published curriculum and may lag behind changes made upstream. Oak's "
        'teacher-facing notes are deliberately not copied here &mdash; follow the '
        'link on any lesson for those.</p>'
        '%s</div>'
        '</div>'
        '<div class="cols cols-1"><div class="col">'
        '<div class="coltitle">Saved progress</div>'
        '<p class="rd" style="font-size:14px;">Exit quiz scores are saved in this '
        'browser only &mdash; nothing is uploaded, and they do not follow you to '
        'another device. Clearing site data clears them.</p>'
        '<p><button type="button" class="btn btn-secondary" data-clear-progress>'
        'Clear saved progress</button> '
        '<span class="rd" data-progress-note></span></p>'
        '</div></div>'
        '</div>'
        % (len(data["units"]), data["totals"]["lessons"],
           "{:,}".format(sum(len(l["starterQuiz"]) + len(l["exitQuiz"])
                             for u in data["units"] for l in u["lessons"])),
           '<p style="margin-top:20px;">%s</p>' % oak_button(
               data["sourceUrl"], "Oak Year 8 maths"))
    )
    write("about.html", page(
        0, "About | %s" % SITE_NAME, body, current="about",
        description="Where this site's curriculum content comes from, and how it is "
                    "licensed.", scripts=("assets/progress.js",)))


def main():
    if not os.path.exists(DATA):
        sys.exit("missing %s -- run the importer first" % DATA)
    with open(DATA, encoding="utf-8") as fh:
        data = json.load(fh)

    with open(RESOURCE_DATA, encoding="utf-8") as fh:
        RESOURCES.update(json.load(fh))

    if os.path.exists(IMAGE_MANIFEST):
        with open(IMAGE_MANIFEST, encoding="utf-8") as fh:
            LOCAL_IMAGES.update(json.load(fh))
        print("using %d vendored quiz images" % len(LOCAL_IMAGES))

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(ASSETS, os.path.join(OUT, "assets"))

    build_home(data)
    build_subject(data)
    build_resources(data)
    build_about(data)
    n = 0
    for u in data["units"]:
        build_unit(data, u)
        ls = u["lessons"]
        for i, l in enumerate(ls):
            build_lesson(data, u, l,
                         ls[i - 1] if i > 0 else None,
                         ls[i + 1] if i + 1 < len(ls) else None)
            n += 1

    print("built %d units, %d lessons -> %s" % (len(data["units"]), n, OUT))


if __name__ == "__main__":
    main()
