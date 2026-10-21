"""Descriptions only; values always come directly from model inference."""
FEATURE_DETAILS = {
    "code_switching_ratio": (
        "Mixing Filipino and English",
        "Smaller of the detected Filipino and English word counts, divided by their combined count. Ambiguous words are excluded; maximum 0.5.",
        "Paghahalo ng Filipino at English",
        "Ang mas maliit na bilang ng natukoy na salitang Filipino o English, hinati sa pinagsamang bilang. Hindi kasama ang mga salitang hindi tiyak ang wika; hanggang 0.5 lamang.",
    ),
    "filipino_particle_frequency": (
        "Filipino particles",
        "Alphabetic tokens matching the saved Filipino-particle list, divided by all non-space tokens, including punctuation.",
        "Mga katagang Filipino",
        "Bilang ng mga salitang tumugma sa naka-save na listahan ng katagang Filipino, hinati sa lahat ng token na hindi espasyo, kasama ang bantas.",
    ),
    "punctuation_intensity": (
        "Exclamation and question marks",
        "Exclamation-mark and question-mark characters divided by all characters.",
        "Tandang padamdam at pananong",
        "Bilang ng tandang padamdam at pananong, hinati sa lahat ng character.",
    ),
    "capitalization_ratio": (
        "Capital letters",
        "Uppercase alphabetic characters divided by all alphabetic characters.",
        "Malalaking titik",
        "Bilang ng malalaking titik, hinati sa lahat ng titik.",
    ),
    "repeated_character_ratio": (
        "Repeated characters",
        "Characters in case-sensitive runs of three or more identical characters, divided by all characters.",
        "Paulit-ulit na character",
        "Mga character sa magkakasunod na tatlo o higit pang eksaktong magkaparehong character, hinati sa lahat ng character.",
    ),
    "emotional_language_frequency": (
        "Emotion-related words",
        "Alphabetic tokens matching the saved emotion-word list, divided by all non-space tokens.",
        "Mga salitang may kaugnayan sa emosyon",
        "Bilang ng mga salitang tumugma sa naka-save na listahan ng salitang emosyonal, hinati sa lahat ng token na hindi espasyo.",
    ),
    "urgency_cue_frequency": (
        "Urgency-related words",
        "Alphabetic tokens matching the saved urgency-word list, divided by all non-space tokens.",
        "Mga salitang nagpapahiwatig ng pagmamadali",
        "Bilang ng mga salitang tumugma sa naka-save na listahan ng salitang nagpapahiwatig ng pagmamadali, hinati sa lahat ng token na hindi espasyo.",
    ),
}


def describe(indicators):
    return [dict(item, display_name=FEATURE_DETAILS[item["name"]][0], definition=FEATURE_DETAILS[item["name"]][1],
                 display_name_tagalog=FEATURE_DETAILS[item["name"]][2], definition_tagalog=FEATURE_DETAILS[item["name"]][3],
                 unit="ratio", zero_denominator="0", interpretation="Text signal; not feature importance or proof of falsehood.") for item in indicators]
