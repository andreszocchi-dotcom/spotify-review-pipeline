"""Deterministic extraction: evidence quote and entities, with no model call.

The quote is always a slice of the original text, so it is an exact substring by construction.
Short reviews quote themselves in full; longer ones quote the sentence that best matches the
chosen topic's terms (or the first sentence when nothing matches).
"""

import re

QUOTE_FULL_TEXT_MAX = 200  # characters; shorter reviews are quoted whole
QUOTE_MAX = 300

TOPIC_TERMS = {
    "access": ["log in", "login", "logged out", "sign in", "sign up", "signup", "password", "account", "verify", "email"],
    "usability": ["shuffle", "queue", "playlist", "button", "layout", "interface", "ui", "navigate", "update", "ads", "ad ",
                  "skip", "design", "widget", "home screen", "library"],
    "playback": ["crash", "stops", "stop playing", "pause", "lag", "buffer", "won't play", "doesn't play", "not playing",
                 "connection", "bluetooth", "audio", "sound", "quality", "battery", "freez", "glitch", "load"],
    "downloads": ["download", "offline", "saved", "storage"],
    "catalog": ["song", "artist", "album", "search", "recommend", "lyrics", "podcast", "discover", "music selection"],
    "billing": ["premium", "pay", "price", "charged", "charge", "subscription", "subscribe", "refund", "money", "free trial",
                "plan", "card"],
    "support": ["support", "customer service", "help center", "contacted", "agent", "response"],
}

# Feature terms reported as entities when they literally appear in the text.
ENTITY_TERMS = sorted({t.strip() for terms in TOPIC_TERMS.values() for t in terms} | {
    "spotify", "car", "android auto", "chromecast", "smart tv", "wear os", "dj", "family plan", "student", "car mode",
    "canvas", "wrapped", "radio", "daily mix", "blend", "sleep timer", "equalizer", "dark mode",
}, key=len, reverse=True)

_SENTENCE = re.compile(r"[^.!?\n]+[.!?]*")


def _sentences(text):
    """(start, end) spans of sentences, trimmed of surrounding whitespace."""
    for m in _SENTENCE.finditer(text):
        s, e = m.span()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            yield s, e


def evidence_quote(text, topic):
    stripped = text.strip()
    if len(stripped) <= QUOTE_FULL_TEXT_MAX:
        return stripped
    terms = TOPIC_TERMS.get(topic, [])
    best, best_hits = None, 0
    for s, e in _sentences(text):
        low = text[s:e].lower()
        hits = sum(low.count(t) for t in terms)
        if hits > best_hits:
            best, best_hits = (s, e), hits
    if best is None:
        best = next(_sentences(text), (0, len(text)))
    s, e = best
    return text[s:min(e, s + QUOTE_MAX)].strip()


def entities(text):
    low = text.lower()
    found = []
    for term in ENTITY_TERMS:
        if re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", low) and not any(term in f for f in found):
            found.append(term)
    return sorted(found)[:8]
