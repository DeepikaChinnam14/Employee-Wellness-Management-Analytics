"""
recommendations.py
Lightweight, dependency-free (no torch/spacy) home for the wellness
recommendation engine, shared by:
  - nlp_pipeline.py  -> get_recommendation() for a single journal entry
  - app.py           -> get_period_recommendation() for a Dashboard
                         date-range PDF export summary

Kept separate from nlp_pipeline.py so app.py (a plain Streamlit process)
doesn't need to import the heavy NLP stack just to build a report.
"""

# ---------------------------------------------------------------------------
# Wellness recommendation engine
#
# Simple rule-based recommender: maps a detected emotion label to a small set
# of curated wellness suggestions. This mirrors what a real MoodMentor-style
# system would do -- detected emotional state -> mapped intervention -- just
# without a database-backed content repository behind it.
#
# The confidence score (0-1) is used to pick *how* urgent/serious the
# suggestion should be for Sad/Stress/Angry/Fear:
#   - low confidence  (< 0.4): the model isn't very sure, so keep it light/generic
#   - medium confidence (0.4-0.7): a normal, matched coping suggestion
#   - high confidence (>= 0.7): the emotion signal is strong, so nudge more
#     firmly towards professional/structured support
#
# Happy and Neutral don't need an urgency ladder -- they always get an
# encouraging or maintenance-style tip instead.
# ---------------------------------------------------------------------------

WELLNESS_RECOMMENDATIONS = {
    "Happy": [
        "Great to see you're feeling good! Take a moment to note what contributed to this — it helps to recognize your own positive patterns.",
        "Keep this momentum going: consider sharing your positive energy with a colleague or teammate today.",
    ],
    "Neutral": [
        "A calm, steady mood is a good baseline. A short 5-minute walk or stretch break can help maintain it.",
        "Nothing urgent here — this could be a good time to plan your day or check in on a personal goal.",
    ],
    "Sad": {
        "low": "It looks like there might be a touch of sadness here. Consider writing a bit more in your journal about what's on your mind.",
        "medium": "Try a short guided breathing exercise (4 seconds in, 4 seconds hold, 4 seconds out) or step outside for a few minutes.",
        "high": "This seems like a strong low mood. Please consider talking to a trusted colleague, friend, or your HR/EAP wellness contact today.",
    },
    "Stress": {
        "low": "A little stress is normal — try a quick 2-minute breathing break before your next task.",
        "medium": "Consider breaking your current task into smaller steps, and take a 10-minute break away from your screen.",
        "high": "Your stress signal looks high. Try a longer break, deep breathing, or a short walk, and consider flagging your workload to your manager or HR.",
    },
    "Angry": {
        "low": "A bit of frustration is showing. A short pause before responding to anything stressful can help.",
        "medium": "Try stepping away for 5-10 minutes before continuing. Cognitive reframing — writing down the situation objectively — can help too.",
        "high": "This reads as strong frustration or anger. Please take a proper break away from the trigger, and consider talking it through with someone you trust or your HR/EAP contact.",
    },
    "Fear": {
        "low": "A little anxiety is showing. Grounding techniques (naming 5 things you can see, 4 you can hear) can help settle it.",
        "medium": "Try a short guided breathing or grounding exercise, and write down specifically what's worrying you — it often feels more manageable on paper.",
        "high": "This looks like a strong fear/anxiety signal. Please consider reaching out to a trusted colleague, your HR/EAP program, or a mental health professional.",
    },
}

# Maps the 5-point manual mood-picker label (db.MOOD_LABELS) onto the same
# 6-label emotion vocabulary above, so entries with no NLP/emotion data
# (manual mood taps) can still be folded into a recommendation.
MOOD_TO_EMOTION_BUCKET = {
    "Amazing": "Happy",
    "Happy": "Happy",
    "Normal": "Neutral",
    "Sad": "Sad",
    "Angry": "Angry",
}


def _confidence_bucket(confidence: float) -> str:
    """Buckets a 0-1 confidence score into low / medium / high urgency."""
    if confidence is None:
        return "medium"
    if confidence < 0.4:
        return "low"
    if confidence < 0.7:
        return "medium"
    return "high"


def get_recommendation(
    emotion_label: str,
    confidence: float = None,
    sentiment: str = None,
    sentiment_score: float = None,
) -> str:
    """
    Returns a wellness suggestion string, combining both classifiers:

    - `emotion_label` / `confidence` come from the BERT emotion model
      (Happy, Sad, Stress, Angry, Fear, Neutral).
    - `sentiment` / `sentiment_score` come from VADER (Positive, Negative,
      Neutral + a compound score from -1 to 1).

    These two models are trained independently and can disagree -- e.g. BERT
    says "Neutral" while VADER's compound score is clearly negative. Relying
    on the emotion label alone would then give a generic "maintenance" tip
    for text that actually reads negative.

    Fix: if BERT's top emotion is "Neutral" but VADER disagrees and calls the
    text "Negative", we treat it as mild Sad/Stress instead of Neutral, using
    the *sentiment* score for urgency instead of the (less reliable, in this
    case) emotion confidence. Otherwise, emotion label + emotion confidence
    drive the recommendation as before.
    """
    effective_label = emotion_label
    effective_confidence = confidence

    if emotion_label == "Neutral" and sentiment == "Negative":
        effective_label = "Sad"
        magnitude = abs(sentiment_score) if sentiment_score is not None else 0.3
        effective_confidence = magnitude  # -1..1 magnitude reused as 0..1 bucket input

    entry = WELLNESS_RECOMMENDATIONS.get(effective_label)
    if entry is None:
        return "Take a moment to check in with yourself today."

    if isinstance(entry, list):
        # Happy / Neutral (and genuinely neutral-sentiment text): no urgency
        # ladder, just rotate suggestions.
        import random
        return random.choice(entry)

    bucket = _confidence_bucket(effective_confidence)
    return entry[bucket]


def get_period_recommendation(entries: list[dict]) -> str:
    """
    Builds a short 2-3 sentence wellness summary for a *set* of mood_logs
    rows (e.g. everything within a Dashboard date-range export), rather
    than a single journal entry.

    Each `entries` item is expected to look like a row from
    db.get_user_mood_history(): at minimum `sentiment` (the 5-point mood
    label), and optionally `emotion` + `confidence` (present only for
    source == 'nlp' journal entries).

    Prefers the richer emotion/confidence data where available and falls
    back to the manual mood-picker label (mapped onto the same bucket
    vocabulary) otherwise, so a period made up of only emoji taps still
    gets a sensible recommendation.
    """
    if not entries:
        return "No entries were logged in this period yet."

    bucket_counts: dict[str, int] = {}
    bucket_confidences: dict[str, list[float]] = {}

    for e in entries:
        if e.get("source") == "nlp" and e.get("emotion"):
            bucket = e["emotion"]
            conf = e.get("confidence")
        else:
            bucket = MOOD_TO_EMOTION_BUCKET.get(e.get("sentiment"), "Neutral")
            conf = None

        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if conf is not None:
            bucket_confidences.setdefault(bucket, []).append(conf)

    total = sum(bucket_counts.values())
    dominant_bucket = max(bucket_counts, key=bucket_counts.get)
    dominant_count = bucket_counts[dominant_bucket]
    pct = round(100 * dominant_count / total)

    confs = bucket_confidences.get(dominant_bucket)
    avg_conf = sum(confs) / len(confs) if confs else None

    tip = get_recommendation(dominant_bucket, avg_conf)

    overview = (
        f"Over this period, {dominant_bucket.lower()} was your most common state "
        f"({dominant_count} of {total} entries, {pct}%)."
    )
    closing = "Keep logging regularly so trends like this are easier to catch early."

    return f"{overview} {tip} {closing}"
