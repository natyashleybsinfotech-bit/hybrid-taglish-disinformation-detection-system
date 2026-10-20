"""Descriptions only; values always come directly from model inference."""
FEATURE_DETAILS = {
    "code_switching_ratio": ("Code-switching ratio", "Smaller of the detected Filipino and English word counts, divided by their combined count. Ambiguous words are excluded; maximum 0.5."),
    "filipino_particle_frequency": ("Filipino particle frequency", "Alphabetic tokens matching the saved particle lexicon, divided by all non-space tokens, including punctuation."),
    "punctuation_intensity": ("Punctuation intensity", "Exclamation and question-mark characters divided by all characters."),
    "capitalization_ratio": ("Capitalization ratio", "Uppercase alphabetic characters divided by all alphabetic characters."),
    "repeated_character_ratio": ("Repeated-character ratio", "Characters in case-sensitive runs of three or more identical characters divided by all characters."),
    "emotional_language_frequency": ("Emotional-language frequency", "Alphabetic tokens matching the saved emotion lexicon divided by all non-space tokens."),
    "urgency_cue_frequency": ("Urgency-cue frequency", "Alphabetic tokens matching the saved urgency lexicon divided by all non-space tokens."),
}


def describe(indicators):
    return [dict(item, display_name=FEATURE_DETAILS[item["name"]][0], definition=FEATURE_DETAILS[item["name"]][1],
                 unit="ratio", zero_denominator="0", interpretation="Text signal; not feature importance or proof of falsehood.") for item in indicators]
