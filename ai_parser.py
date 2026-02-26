"""Smart natural language parser using spaCy NER."""

import logging

logger = logging.getLogger(__name__)

_nlp = None


def _get_nlp():
    """Lazy-load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning(
                "spaCy model not found. Run: python -m spacy download en_core_web_sm"
            )
            return None
    return _nlp


def parse_with_spacy(text: str) -> dict | None:
    """
    Parse natural language text to extract idea and time using spaCy NER.

    Returns dict with keys:
        - idea: str (the task/idea to schedule)
        - time_str: str (extracted time expression)

    Returns None if:
        - spaCy model not installed
        - No time entities found
    """
    nlp = _get_nlp()
    if not nlp:
        return None

    doc = nlp(text)

    # Extract DATE and TIME entities
    time_entities = []
    for ent in doc.ents:
        if ent.label_ in ("DATE", "TIME"):
            time_entities.append((ent.start_char, ent.end_char, ent.text))

    if not time_entities:
        return None

    # Sort by position and combine adjacent time entities
    time_entities.sort(key=lambda x: x[0])

    # Build time string from all time entities
    time_parts = [ent[2] for ent in time_entities]
    time_str = " ".join(time_parts)

    # Remove time entities from text to get the idea
    idea_chars = list(text)
    # Mark characters that are part of time entities
    for start, end, _ in time_entities:
        for i in range(start, end):
            idea_chars[i] = None

    # Reconstruct idea without time parts
    idea = "".join(c for c in idea_chars if c is not None)

    # Clean up the idea text
    idea = " ".join(idea.split())  # Normalize whitespace
    idea = idea.strip(" ,-:")  # Remove leading/trailing punctuation

    # Skip if idea is too short or empty
    if not idea or len(idea) < 3:
        return None

    return {
        "idea": idea,
        "time_str": time_str,
    }


def is_spacy_available() -> bool:
    """Check if spaCy parsing is available (model installed)."""
    return _get_nlp() is not None


# Backwards compatibility alias
def parse_with_ai(text: str, user_timezone: str = None) -> dict | None:
    """Alias for parse_with_spacy (backwards compatibility)."""
    result = parse_with_spacy(text)
    if result:
        # Add confidence field for compatibility
        result["confidence"] = 0.8
    return result


def is_ai_available() -> bool:
    """Alias for is_spacy_available (backwards compatibility)."""
    return is_spacy_available()
