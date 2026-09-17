"""Read the JSON payload out of a Next.js app-router (RSC "flight") HTML page."""
import re
import json

PUSH = re.compile(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)')


def flight_text(html):
    parts = []
    for m in PUSH.finditer(html):
        try:
            parts.append(json.loads('"' + m.group(1) + '"'))
        except ValueError:
            pass
    return ''.join(parts)


STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)


def blank_strings(text):
    """Copy of `text` with every string literal's contents replaced by spaces.

    Braces inside strings must not be counted when walking out to an enclosing
    object -- Oak's short-answer quiz stems contain `{{ }}` answer placeholders,
    which otherwise throw the brace depth off. Blanking keeps every character
    at its original offset, so indices stay interchangeable with `text`.
    """
    return STRING_LITERAL.sub(lambda m: '"' + ' ' * (m.end() - m.start() - 2) + '"',
                              text)


def find_object(text, key, start=0, skeleton=None, require=()):
    """Return (obj, next_start) for a JSON object enclosing an occurrence of `key`.

    Occurrences are tried in order until one decodes into a dict holding every
    name in `require`; that guards against matching a smaller nested object or
    an unrelated structure that happens to carry the same key.
    """
    if skeleton is None:
        skeleton = blank_strings(text)
    needle = '"%s"' % key
    pos = start
    while True:
        i = text.find(needle, pos)
        if i < 0:
            return None, -1
        pos = i + 1
        # Walk back to the opening brace of the enclosing object. The skeleton
        # has no braces inside string literals, so plain counting is safe.
        depth = 0
        j = i
        while j >= 0:
            c = skeleton[j]
            if c == '}':
                depth += 1
            elif c == '{':
                if depth == 0:
                    break
                depth -= 1
            j -= 1
        if j < 0:
            continue
        try:
            obj, end = json.JSONDecoder().raw_decode(text, j)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if require and not all(k in obj for k in require):
            continue
        return obj, j + end
