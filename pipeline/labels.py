"""Shared label definitions (GRADING_CONTRACT.md) and the Jev question set built from them.

Everything that changes what the classifier sees lives here, and LABEL_CONFIG names it.
Bump PROMPT_VERSION whenever a definition, instruction or option changes: cached results
are keyed by text + LABEL_CONFIG, so a new version forces fresh work instead of reuse.
"""

from typesafe_sdk import Choice, Score

JEV_MODEL = "jev-1.13.0"  # pinned; "jev-latest" resolved to this on 2026-10-16
PROMPT_VERSION = "labels-v1"
SCHEMA_VERSION = "schema-v1"
LABEL_CONFIG = f"{JEV_MODEL}+{PROMPT_VERSION}+{SCHEMA_VERSION}"

TOPICS = {
    "access": "Login, signup, password or account access problems.",
    "usability": "Navigation, controls, layout, queue/playlist management, shuffle behaviour, ad interruptions.",
    "playback": "Playback failure, crashes, lag, connection failures, audio quality, battery/data/storage use.",
    "downloads": "Downloading, saved music, offline listening, disappearing downloads.",
    "catalog": "Missing songs/artists, search/discovery, recommendations, lyrics availability.",
    "billing": "Price, charges, subscriptions, paywalls, premium entitlement, features locked to premium.",
    "support": "Contacting customer support and the support response.",
    "other": "General praise or criticism with no specific feature, unrelated content, or no supported topic.",
}

TOPIC_INSTRUCTIONS = (
    "Classify the review text only. If several problems are mentioned, pick the one with the highest "
    "severity; on a tie, the first one mentioned. For a positive review pick the first specific praised "
    "feature; general praise is 'other'. Mentioning a paid plan alone is not 'billing': a subscription "
    "failing to activate is billing, music crashing for a paying user is playback."
)

INTENTS = {
    "cancellation": "Explicitly leaving, uninstalling, cancelling, switching away, or threatening to.",
    "complaint": "A negative experience, including mixed praise and criticism, or a generic 'bad app'.",
    "request": "Asks for a change or new feature without reporting a failure.",
    "praise": "Positive about the app with no complaint.",
    "unclear": "Meaningless, unrelated, or a bare boycott slogan with no product complaint or personal departure.",
}

INTENT_INSTRUCTIONS = (
    "Classify the review text only; ignore any star rating. Precedence when several apply: "
    "cancellation, then complaint, then request, then praise, then unclear."
)

SEVERITY = {
    "1": "No reported problem: praise, neutral or unclear content, or a pure feature request.",
    "2": "Dislike, generic criticism, minor annoyance or cosmetic issue; no functional loss described.",
    "3": "A function is degraded or restricted, but some use or a workaround remains.",
    "4": "A core task is clearly blocked, such as being unable to log in or play music at all.",
    "5": "Explicit serious financial, privacy or data harm (e.g. charged without consent, account hacked, library wiped).",
}

SEVERITY_INSTRUCTIONS = (
    "Rate the most severe problem the text actually reports. Angry language, an expensive plan, "
    "a crash alone, or saying they will cancel does not raise severity. Do not assume impact the text does not state."
)

SENTIMENT_LEVELS = ["very negative", "negative", "neutral or mixed", "positive", "very positive"]


def questions():
    """One Jev call per review asks all four questions."""
    return {
        "topic": Choice(instructions=TOPIC_INSTRUCTIONS, criteria=TOPICS),
        "intent": Choice(instructions=INTENT_INSTRUCTIONS, criteria=INTENTS),
        "severity": Choice(instructions=SEVERITY_INSTRUCTIONS, criteria=SEVERITY),
        "sentiment": Score(instructions="Overall sentiment of the review text.", criteria=SENTIMENT_LEVELS),
    }


def sentiment_from_score(score):
    """Jev Score position 0..4 -> sentiment -1..1 (the assignment's mapping)."""
    return round(score / 2 - 1, 3)
