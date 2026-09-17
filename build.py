#!/usr/bin/env python3
"""Generate the Year 8 Study Hub static site from data/curriculum/*.json.

Plain HTML on the Modernist stylesheet -- no framework, no build toolchain.
Run `python build.py` and open site/index.html.
"""
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CURRICULUM_DIR = os.path.join(ROOT, "data", "curriculum")
RESOURCE_DATA = os.path.join(ROOT, "data", "resources.json")
OUT = os.path.join(ROOT, "site")
ASSETS = os.path.join(ROOT, "assets")
IMAGE_MANIFEST = os.path.join(ASSETS, "quiz-images", "manifest.json")

# Populated when tools/fetch_images.py has vendored the quiz images; otherwise
# the pages hotlink Oak's CDN.
LOCAL_IMAGES = {}

# Our own resources, loaded from data/resources.json in main().
RESOURCES = {}

# {subject-slug: curriculum}, loaded from data/curriculum/ in main().
CURRICULA = {}

SITE_NAME = "Year 8 Study Hub"

# The wireframe's subject grid, in its order. A subject goes live as soon as
# data/curriculum/<slug>.json exists; the rest show as placeholders rather
# than dead links.
SUBJECT_ORDER = [
    ("english", "English"),
    ("maths", "Maths"),
    ("science", "Science"),
    ("art", "Art"),
    ("geography", "Geography"),
    ("history", "History"),
]

BLANK = re.compile(r"\{\{\s*\}\}")


def ready_subjects():
    """Subject slugs with curriculum data, in the wireframe's order."""
    return [s for s, _t in SUBJECT_ORDER if s in CURRICULA]


def subject_title(slug):
    return CURRICULA[slug]["subject"] if slug in CURRICULA else slug.title()


def unit_key(subject, unit_slug):
    return "%s/%s" % (subject, unit_slug)


def lesson_key(subject, unit_slug, lesson_slug):
    return "%s/%s/%s" % (subject, unit_slug, lesson_slug)


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
        return '<a href="%s%s"%s>%s</a>' % (up(depth), href, cur, esc(label))

    links = [link("index.html", "Subjects", "home")]
    for slug in ready_subjects():
        links.append(link("%s/index.html" % slug, subject_title(slug), slug))
    links.append(link("resources.html", "Resources", "resources"))
    links.append(link("about.html", "About", "about"))

    return (
        '<nav class="nav">'
        '<div class="nav-brand"><a href="%sindex.html">%s</a></div>'
        '%s</nav>' % (up(depth), SITE_NAME, "".join(links))
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


MANIFEST = ".build-manifest"

# Every path this build produces under site/, recorded so the next build can
# tell its own output apart from anything a human dropped in there.
WRITTEN = set()


def write(relpath, content):
    path = os.path.join(OUT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    WRITTEN.add(relpath.replace(os.sep, "/"))


def existing_files():
    out = set()
    for base, _dirs, files in os.walk(OUT):
        for f in files:
            rel = os.path.relpath(os.path.join(base, f), OUT)
            out.add(rel.replace(os.sep, "/"))
    return out


def strays():
    """Files under site/ that the previous build did not create.

    site/ is disposable -- every build wipes it -- so a file saved in there by
    hand is lost on the next run. Rather than delete someone's work silently,
    bail out and say where it should live instead."""
    manifest_path = os.path.join(OUT, MANIFEST)
    if not os.path.isdir(OUT) or not os.path.exists(manifest_path):
        return set()  # nothing to compare against; assume a clean slate
    with open(manifest_path, encoding="utf-8") as fh:
        known = {line.strip() for line in fh if line.strip()}
    known.add(MANIFEST)
    return existing_files() - known


def record_assets():
    base = os.path.join(OUT, "assets")
    for root, _dirs, files in os.walk(base):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), OUT)
            WRITTEN.add(rel.replace(os.sep, "/"))


# ── quiz rendering ────────────────────────────────────────────────────────────

def render_question(q, idx, quiz_id, depth=3):
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
                '<input type="%s" name="%s-q%d" value="%d">'
                '<span class="box"></span><span class="txt">%s</span></label>'
                % ("1" if o["correct"] else "0", kind, esc(quiz_id), idx, oi,
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


def render_quiz(title, questions, quiz_id, key):
    """A quiz lives in a <dialog>; the page shows only a button that opens it."""
    if not questions:
        return "", ""
    qs = "".join(render_question(q, i + 1, quiz_id)
                 for i, q in enumerate(questions))
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
        % (esc(quiz_id), esc(quiz_id), esc(key), len(questions),
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
    """The wireframe's two columns, ours first: what we keep is the point of
    the site, references are backup."""
    links = [r for r in items if resource_group(r) == "links"]
    ours = [r for r in items if resource_group(r) == "ours"]

    def col(title, rows, hint):
        if rows:
            body = "".join(resource_row(r, depth) for r in rows)
        else:
            body = '<p class="rd resempty">%s</p>' % hint
        return '<div class="col"><div class="coltitle">%s</div>%s</div>' % (title, body)

    return (
        '<div class="cols">%s%s</div>'
        % (col("Our resources", ours, empty_hint or "Nothing here yet."),
           col("Relevant links", links, empty_hint or "Nothing here yet."))
    )


def resources_for(scope, key=None):
    if scope == "general":
        return RESOURCES.get("general") or []
    return (RESOURCES.get(scope) or {}).get(key) or []


def add_hint(flag, key):
    return ('Nothing here yet &mdash; add one with '
            '<code>python tools/add_resource.py %s %s --file &lt;path&gt; '
            '--title "…"</code>' % (flag, esc(key)))


def unregistered_resources():
    """Files in assets/resources/ that nothing in resources.json points at.

    Dropping a file in the folder is not enough -- the pages only render what
    is registered -- and the failure is silent, so say so at build time."""
    registered = set()
    for r in RESOURCES.get("general") or []:
        registered.add(r.get("url", ""))
    for scope in ("units", "lessons"):
        for items in (RESOURCES.get(scope) or {}).values():
            for r in items:
                registered.add(r.get("url", ""))

    base = os.path.join(ASSETS, "resources")
    loose = []
    for root, _dirs, files in os.walk(base):
        for f in files:
            if f in (".gitkeep", "README.md"):
                continue
            rel = os.path.relpath(os.path.join(root, f), ROOT)
            rel = rel.replace(os.sep, "/")
            if rel not in registered:
                loose.append(rel)
    return sorted(loose)


def render_pager(prev_item, next_item, noun):
    """Previous/next strip. Units and lessons are both siblings one level up,
    so the same relative href shape works for either."""
    def cell(item, side, label):
        if not item:
            return ('<span class="%s"><span class="lbl">%s</span>'
                    '<span class="ttl text-muted">&mdash;</span></span>'
                    % (side, esc(label)))
        return ('<a class="%s" href="../%s/index.html"><span class="lbl">%s</span>'
                '<span class="ttl">%s</span></a>'
                % (side, esc(item["slug"]), esc(label), esc(item["title"])))

    return ('<div class="pager">%s%s</div>'
            % (cell(prev_item, "prev", "Previous %s" % noun),
               cell(next_item, "next", "Next %s" % noun)))


def render_guidance(items):
    """Oak's content warnings. English leans on these; maths rarely has any."""
    if not items:
        return ""
    rows = []
    for g in items:
        # Escape each part, then join with the entity -- escaping the joined
        # string would turn the separator into a literal "&middot;".
        detail = " &middot; ".join(
            esc(x) for x in (g.get("description"), g.get("area")) if x)
        rows.append('<div class="resrow"><span><span class="rt">%s</span>'
                    '<span class="rd">%s</span></span></div>'
                    % (esc(g.get("label", "")), detail))
    return (
        '<div class="cols cols-1"><div class="col guidance">'
        '<div class="coltitle"><span class="tag tag-outline">Content guidance</span>'
        '</div>%s</div></div>' % "".join(rows)
    )


# ── pages ─────────────────────────────────────────────────────────────────────

def build_home():
    totals = {"units": 0, "lessons": 0, "questions": 0}
    for data in CURRICULA.values():
        totals["units"] += data["totals"]["units"]
        totals["lessons"] += data["totals"]["lessons"]
        totals["questions"] += sum(
            len(l["starterQuiz"]) + len(l["exitQuiz"])
            for u in data["units"] for l in u["lessons"])

    cards = []
    for i, (slug, title) in enumerate(SUBJECT_ORDER, 1):
        if slug in CURRICULA:
            d = CURRICULA[slug]
            cards.append(
                '<a class="card" href="%s/index.html">'
                '<div class="card-kicker">%02d</div>'
                '<div class="card-title">%s</div>'
                '<div class="card-meta">%d units &middot; %d lessons</div></a>'
                % (esc(slug), i, esc(d["subject"]),
                   d["totals"]["units"], d["totals"]["lessons"]))
        else:
            cards.append(
                '<div class="card is-pending"><div class="card-kicker">%02d</div>'
                '<div class="card-title">%s</div>'
                '<div class="card-meta">Not yet added</div></div>'
                % (i, esc(title)))

    body = (
        '<div class="wrap">'
        '<p class="kicker">Homeschool companion</p>'
        '<h1 style="max-width:820px;font-size:48px;">Resources built alongside the '
        'Oak Academy Year 8 curriculum.</h1>'
        '<p class="lede" style="font-size:16px;">Every unit and lesson links back to '
        'the matching Oak Academy lesson, with the learning points, keywords and '
        'quizzes, alongside the resources we keep.</p>'
        '<div class="factrow">'
        '<div class="fact"><div class="n">%d</div><div class="l">Units</div></div>'
        '<div class="fact"><div class="n">%d</div><div class="l">Lessons</div></div>'
        '<div class="fact"><div class="n">%s</div><div class="l">Quiz questions</div></div>'
        '</div>'
        '<div class="hr" style="margin-bottom:40px;"></div>'
        '<h2 class="sectiontitle">Subjects &mdash; Year 8</h2>'
        '<div class="grid6">%s</div>'
        '</div>'
        % (totals["units"], totals["lessons"], "{:,}".format(totals["questions"]),
           "".join(cards))
    )
    write("index.html", page(
        0, "%s — Year 8 homeschool resources" % SITE_NAME, body, current="home",
        description="Year 8 homeschool study hub built alongside the Oak National "
                    "Academy curriculum."))


def build_subject(data):
    slug = data["subjectSlug"]
    units = data["units"]
    cards = []
    for u in units:
        ukey = unit_key(slug, u["slug"])
        n_res = len(resources_for("units", ukey)) + sum(
            len(resources_for("lessons", lesson_key(slug, u["slug"], l["slug"])))
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
               esc(u["description"]), len(u["lessons"]), res_meta, esc(ukey)))

    body = (
        crumb(1, [("Home", "index.html"), (data["subject"], None),
                  ("Year %s" % data["year"], None)])
        + '<div class="wrap">'
        '<div class="pagehead"><h1>%s &mdash; Year %s</h1>%s</div>'
        '<p class="lede">Units run in Oak Academy\'s Year %s sequence. '
        '%d units, %d lessons.</p>'
        '<div class="unitlist">%s</div>'
        '</div>'
        % (esc(data["subject"]), esc(str(data["year"])),
           oak_button(data["sourceUrl"]), esc(str(data["year"])),
           len(units), data["totals"]["lessons"], "".join(cards))
    )
    write("%s/index.html" % slug, page(
        1, "%s — Year %s | %s" % (data["subject"], data["year"], SITE_NAME), body,
        current=slug,
        description="All %d Year %s %s units from the Oak National Academy "
                    "curriculum." % (len(units), data["year"],
                                     data["subject"].lower()),
        scripts=("assets/progress.js",)))


def build_unit(data, u, prev_u, next_u):
    slug = data["subjectSlug"]
    ukey = unit_key(slug, u["slug"])

    rows = []
    for l in u["lessons"]:
        lkey = lesson_key(slug, u["slug"], l["slug"])
        n_res = len(resources_for("lessons", lkey))
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
            % (esc(l["slug"]), esc(lkey), l["order"] or 0, esc(l["title"]),
               esc(l["outcome"]), badges))

    threads = ""
    if u["threads"]:
        threads = " ".join('<span class="tag tag-accent">%s</span>' % esc(t)
                           for t in u["threads"])

    body = (
        crumb(2, [("Home", "index.html"),
                  (data["subject"], "%s/index.html" % slug),
                  ("Year %s" % data["year"], "%s/index.html" % slug),
                  (u["title"], None)])
        + '<div class="wrap">'
        '<p class="kicker">Unit %d of %d</p>'
        '<div class="pagehead"><h1>%s</h1>%s</div>'
        '<p class="lede">%s</p>'
        '%s'
        '<h2 class="sectiontitle" style="margin:48px 0 0;">Unit resources</h2>'
        '%s'
        '<div class="lessonshead">'
        '<h2 class="sectiontitle" style="margin:48px 0 0;">%d lessons</h2>'
        '<span class="unitprog" data-unit="%s" hidden></span></div>'
        '<div class="hr" style="margin:12px 0 8px;"></div>'
        '%s'
        '%s'
        '</div>'
        % (u["index"], len(data["units"]), esc(u["title"]), oak_button(u["oakUrl"]),
           esc(u["description"]),
           ('<p style="margin:-24px 0 32px;">%s</p>' % threads) if threads else "",
           resource_columns(resources_for("units", ukey), 2,
                            add_hint("--unit", ukey)),
           len(u["lessons"]), esc(ukey), "".join(rows),
           render_pager(prev_u, next_u, "unit"))
    )
    write("%s/%s/index.html" % (slug, u["slug"]), page(
        2, "%s | %s Year %s | %s" % (u["title"], data["subject"], data["year"],
                                     SITE_NAME),
        body, current=slug, description=u["description"],
        scripts=("assets/progress.js",)))


def build_lesson(data, u, l, prev_l, next_l):
    slug = data["subjectSlug"]
    lkey = lesson_key(slug, u["slug"], l["slug"])

    cols = []
    if l["keyLearningPoints"]:
        items = "".join("<li>%s</li>" % esc(k) for k in l["keyLearningPoints"])
        cols.append('<div class="col"><div class="coltitle">Key learning points</div>'
                    '<ol class="numlist">%s</ol></div>' % items)
    if l["keywords"]:
        rows = "".join(
            '<div class="resrow"><span><span class="rt">%s</span>'
            '<span class="rd">%s</span></span></div>'
            % (esc(k["word"]), esc(k["definition"])) for k in l["keywords"])
        cols.append('<div class="col"><div class="coltitle">Keywords</div>%s</div>' % rows)
    block1 = ('<div class="cols%s">%s</div>'
              % ("" if len(cols) == 2 else " cols-1", "".join(cols))) if cols else ""

    equipment = ""
    if l.get("equipment"):
        rows = "".join('<div class="resrow"><span class="rt">%s</span></div>' % esc(e)
                       for e in l["equipment"])
        equipment = ('<div class="cols cols-1"><div class="col">'
                     '<div class="coltitle">Equipment</div>%s</div></div>' % rows)

    # The reason the site exists: what we keep for this lesson.
    resources = (
        '<h2 class="sectiontitle" style="margin:48px 0 0;">Resources</h2>'
        + resource_columns(resources_for("lessons", lkey), 3,
                           add_hint("--lesson", lkey))
    )

    starter_btn, starter_dlg = render_quiz(
        "Starter quiz", l["starterQuiz"], "starter", lkey)
    exit_btn, exit_dlg = render_quiz("Exit quiz", l["exitQuiz"], "exit", lkey)
    quizzes = ""
    if starter_btn or exit_btn:
        quizzes = (
            '<h2 class="sectiontitle" style="margin:48px 0 0;">Quizzes</h2>'
            '<div class="cols cols-1"><div class="col">'
            '<div class="quizlaunch" data-lesson="%s">%s%s</div>'
            '<p class="quizstate" data-lesson-state hidden></p>'
            '</div></div>%s%s'
            % (esc(lkey), starter_btn, exit_btn, starter_dlg, exit_dlg))

    pager = render_pager(prev_l, next_l, "lesson")

    body = (
        crumb(3, [("Home", "index.html"),
                  (data["subject"], "%s/index.html" % slug),
                  ("Year %s" % data["year"], "%s/index.html" % slug),
                  (u["title"], "%s/%s/index.html" % (slug, u["slug"])),
                  (l["title"], None)])
        + '<div class="wrap">'
        '<div class="pagehead"><div>'
        '<div class="tag tag-accent" style="margin-bottom:12px;">Lesson %d of %d</div>'
        '<h1>%s</h1></div>%s</div>'
        '<p class="lede" style="margin-bottom:0;">%s</p>'
        '%s%s%s%s%s%s'
        '</div>'
        % (l["order"] or 0, len(u["lessons"]), esc(l["title"]),
           oak_button(l["oakUrl"]), esc(l["outcome"]),
           render_guidance(l.get("contentGuidance")),
           block1, equipment, resources, quizzes, pager)
    )
    write("%s/%s/%s/index.html" % (slug, u["slug"], l["slug"]), page(
        3, "%s | %s | %s" % (l["title"], u["title"], SITE_NAME), body,
        current=slug, description=l["outcome"],
        scripts=("assets/progress.js", "assets/quiz.js")))


def build_resources():
    """One page listing everything we keep, so it is all reachable from one place."""
    total = 0
    sections = []

    general = resources_for("general")
    total += len(general)
    sections.append(
        '<h2 class="sectiontitle" style="margin:0 0 0;">General</h2>'
        + resource_columns(general, 0, add_hint("--general", "").rstrip()))

    for subject in ready_subjects():
        data = CURRICULA[subject]
        blocks = []
        sub_total = 0
        for u in data["units"]:
            ukey = unit_key(subject, u["slug"])
            rows = [resource_row(r, 0) for r in resources_for("units", ukey)]
            for l in u["lessons"]:
                lkey = lesson_key(subject, u["slug"], l["slug"])
                for r in resources_for("lessons", lkey):
                    rows.append(
                        '<div class="resgroup"><a class="resfrom" href="%s/%s/%s/'
                        'index.html">Lesson %d &mdash; %s</a>%s</div>'
                        % (esc(subject), esc(u["slug"]), esc(l["slug"]),
                           l["order"] or 0, esc(l["title"]), resource_row(r, 0)))
            if not rows:
                continue
            sub_total += len(rows)
            blocks.append(
                '<h3 class="sectiontitle" style="margin:32px 0 0;">'
                '<a href="%s/%s/index.html">Unit %d &mdash; %s</a></h3>'
                '<div class="cols cols-1"><div class="col">%s</div></div>'
                % (esc(subject), esc(u["slug"]), u["index"], esc(u["title"]),
                   "".join(rows)))
        if not blocks:
            continue
        total += sub_total
        sections.append(
            '<h2 class="sectiontitle" style="margin:48px 0 0;">'
            '<a href="%s/index.html">%s</a></h2>%s'
            % (esc(subject), esc(data["subject"]), "".join(blocks)))

    body = (
        crumb(0, [("Home", "index.html"), ("Resources", None)])
        + '<div class="wrap">'
        '<div class="pagehead"><h1>Resources</h1></div>'
        '<p class="lede">Everything we keep, in one place. %d item%s. '
        'Anything attached to a unit or a lesson also shows up on that page.</p>'
        '%s'
        '<div class="cols cols-1" style="margin-top:48px;"><div class="col">'
        '<div class="coltitle">Adding a resource</div>'
        '<p class="rd" style="font-size:14px;">Hand it the file and it goes in the '
        'right folder for you:</p>'
        '<pre class="cmd">python tools/add_resource.py --lesson SUBJECT/UNIT/LESSON \\\n'
        '    --file &lt;path&gt; --title "Title"\n\n'
        'python tools/add_resource.py --unit SUBJECT/UNIT --title "…" --url "https://…"\n'
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


def build_about():
    rows = []
    for subject in ready_subjects():
        d = CURRICULA[subject]
        q = sum(len(l["starterQuiz"]) + len(l["exitQuiz"])
                for u in d["units"] for l in u["lessons"])
        rows.append(
            '<div class="resrow"><span><span class="rt">%s &mdash; Year %s</span>'
            '<span class="rd">%d units, %d lessons, %s quiz questions</span></span>'
            '<span class="tag tag-neutral">%s</span></div>'
            % (esc(d["subject"]), esc(str(d["year"])), d["totals"]["units"],
               d["totals"]["lessons"], "{:,}".format(q), esc(d["programme"])))

    body = (
        crumb(0, [("Home", "index.html"), ("About", None)])
        + '<div class="wrap">'
        '<h1>About this site</h1>'
        '<p class="lede">A homeschool study hub for Year 8, built directly on the '
        'Oak National Academy curriculum sequence.</p>'
        '<div class="cols">'
        '<div class="col"><div class="coltitle">What is here</div>%s'
        '<div class="resrow"><span><span class="rt">Learning points and keywords</span>'
        '<span class="rd">Each lesson carries its pupil outcome, key learning points '
        'and keyword definitions.</span></span></div>'
        '<div class="resrow"><span><span class="rt">Our resources</span>'
        '<span class="rd">Links, worksheets and notes we keep, attached to the unit '
        'or lesson they belong to.</span></span></div>'
        '<div class="resrow"><span><span class="rt">Quizzes</span>'
        '<span class="rd">Every starter and exit quiz, answerable in the browser with '
        'hints, marking and feedback.</span></span></div>'
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
        '</div>'
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
        % "".join(rows)
    )
    write("about.html", page(
        0, "About | %s" % SITE_NAME, body, current="about",
        description="Where this site's curriculum content comes from, and how it is "
                    "licensed.", scripts=("assets/progress.js",)))


def load_curricula():
    for path in sorted(glob.glob(os.path.join(CURRICULUM_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        slug = data.get("subjectSlug") or os.path.splitext(os.path.basename(path))[0]
        data["subjectSlug"] = slug
        CURRICULA[slug] = data
    unknown = [s for s in CURRICULA if s not in dict(SUBJECT_ORDER)]
    if unknown:
        print("note: %s not in SUBJECT_ORDER, so %s will not appear on the "
              "homepage grid" % (", ".join(unknown),
                                 "it" if len(unknown) == 1 else "they"))


def main():
    if not os.path.isdir(CURRICULUM_DIR):
        sys.exit("missing %s -- run the importer first" % CURRICULUM_DIR)
    load_curricula()
    if not CURRICULA:
        sys.exit("no curriculum files in %s -- run tools/import_oak.py --all"
                 % CURRICULUM_DIR)

    with open(RESOURCE_DATA, encoding="utf-8") as fh:
        RESOURCES.update(json.load(fh))

    if os.path.exists(IMAGE_MANIFEST):
        with open(IMAGE_MANIFEST, encoding="utf-8") as fh:
            LOCAL_IMAGES.update(json.load(fh))
        print("using %d vendored quiz images" % len(LOCAL_IMAGES))

    loose = strays()
    if loose and "--force" not in sys.argv:
        print("Refusing to rebuild: site/ holds %d file%s this build did not "
              "create." % (len(loose), "" if len(loose) == 1 else "s"))
        for rel in sorted(loose)[:20]:
            print("    site/%s" % rel)
        if len(loose) > 20:
            print("    ... and %d more" % (len(loose) - 20))
        print("\nsite/ is generated -- every build wipes it, so files saved there "
              "by hand are lost.\nPut resources in assets/resources/ instead, then "
              "register one with:\n"
              "    python tools/add_resource.py --unit SUBJECT/UNIT --title \"...\" \\\n"
              "        --file <path>\n"
              "\nMove those files somewhere safe, then rebuild. "
              "`python build.py --force` wipes them.")
        return 1

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(ASSETS, os.path.join(OUT, "assets"))
    record_assets()

    build_home()
    build_resources()
    build_about()

    n_units = n_lessons = 0
    for subject in ready_subjects():
        data = CURRICULA[subject]
        build_subject(data)
        units = data["units"]
        for i, u in enumerate(units):
            build_unit(data, u,
                       units[i - 1] if i > 0 else None,
                       units[i + 1] if i + 1 < len(units) else None)
            ls = u["lessons"]
            for j, l in enumerate(ls):
                build_lesson(data, u, l,
                             ls[j - 1] if j > 0 else None,
                             ls[j + 1] if j + 1 < len(ls) else None)
                n_lessons += 1
            n_units += 1
        print("  %-9s %2d units, %3d lessons"
              % (data["subject"], data["totals"]["units"],
                 data["totals"]["lessons"]))

    with open(os.path.join(OUT, MANIFEST), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(WRITTEN)) + "\n")

    print("built %d subjects, %d units, %d lessons -> %s"
          % (len(ready_subjects()), n_units, n_lessons, OUT))

    loose_res = unregistered_resources()
    if loose_res:
        print("\n%d file%s in assets/resources/ %s not registered, so %s not "
              "linked from any page:"
              % (len(loose_res), "" if len(loose_res) == 1 else "s",
                 "is" if len(loose_res) == 1 else "are",
                 "it is" if len(loose_res) == 1 else "they are"))
        for rel in loose_res[:10]:
            print("    %s" % rel)
        if len(loose_res) > 10:
            print("    ... and %d more" % (len(loose_res) - 10))
        print("Register with:  python tools/add_resource.py "
              "--general|--unit SUBJECT/UNIT|--lesson SUBJECT/UNIT/LESSON \\\n"
              "                    --url <filename> --title \"...\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
