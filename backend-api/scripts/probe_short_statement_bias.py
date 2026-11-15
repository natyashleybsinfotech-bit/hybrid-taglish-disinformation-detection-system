"""Read-only, balanced short-statement bias probe for the active hybrid classifier.

Earlier diagnostics (docs/MODEL-SANITY-DIAGNOSTIC.json) used 10 unlabeled short
statements and found 10/10 predicted "Misleading". That probe could not tell
bias apart from a genuinely-misleading sample. This script fixes that by using
a hand-labeled, balanced set of short Facebook/video-transcript-style
statements -- half written to be genuinely neutral/true, half written to be
genuinely misleading/false -- across English, Tagalog and Taglish code-switch.

This script never trains, tunes, or changes the decision threshold, and it
does not store any submitted text beyond this probe's own output file.

Usage (run locally, from backend-api/):
    python scripts/probe_short_statement_bias.py
"""

import argparse
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.model_runtime import runtime  # noqa: E402

# Ground truth is assigned by construction: each statement below was written
# to be unambiguously one class or the other by a human, independent of what
# the model predicts. "label" is the intended ground truth, not a model output.
PROBE_SET = [
    # ---- Genuinely NON-MISLEADING (neutral/true, short, FB/video-transcript style) ----
    {"text": "Bukas magsisimula na ang klase sa mga paaralang naka-set sa August 1 schedule.", "label": "Non-Misleading", "note": "neutral schedule statement"},
    {"text": "The LRT-2 line will have a shorter operating schedule this weekend due to maintenance.", "label": "Non-Misleading", "note": "neutral transit notice"},
    {"text": "Maulan daw sa Metro Manila ngayong hapon ayon sa PAGASA forecast.", "label": "Non-Misleading", "note": "routine weather forecast"},
    {"text": "Our barangay will hold a free vaccination drive this Saturday at the covered court.", "label": "Non-Misleading", "note": "routine community announcement"},
    {"text": "Marami pong dumalo sa flag ceremony ngayong umaga bago magsimula ang klase.", "label": "Non-Misleading", "note": "mundane school event recap"},
    {"text": "The mayor inaugurated a new public market in the city today.", "label": "Non-Misleading", "note": "routine local news"},
    {"text": "Pasok pa rin bukas, walang suspension sa classes dahil maganda ang lagay ng panahon.", "label": "Non-Misleading", "note": "no-class-suspension notice"},
    {"text": "DOH reminds the public to drink plenty of water during the hot season.", "label": "Non-Misleading", "note": "generic health reminder"},
    {"text": "Grabe yung traffic sa EDSA kanina, umabot ng two hours ang byahe ko.", "label": "Non-Misleading", "note": "personal anecdote, true-sounding"},
    {"text": "The national team will play their next friendly match next month.", "label": "Non-Misleading", "note": "routine sports update"},
    {"text": "Uupdate lang po kami sa schedule ng pickup ng basura sa barangay namin.", "label": "Non-Misleading", "note": "routine LGU update"},
    {"text": "Congratulations to this year's batch of graduates from our local high school.", "label": "Non-Misleading", "note": "celebratory, factual"},
    {"text": "Bagong grocery store ang bubuksan sa tabi ng aming subdivision sa isang buwan.", "label": "Non-Misleading", "note": "neutral local development"},
    {"text": "The DepEd released the school calendar for the coming academic year.", "label": "Non-Misleading", "note": "routine institutional announcement"},
    {"text": "Ang init talaga ngayong tag-init, mag-ingat po sa heat stroke.", "label": "Non-Misleading", "note": "common-sense weather advisory"},
    {"text": "A new jeepney route was approved to serve the growing subdivision.", "label": "Non-Misleading", "note": "routine transport update"},
    {"text": "Sarado po ang aming opisina sa darating na pista opisyal.", "label": "Non-Misleading", "note": "routine holiday notice"},
    {"text": "The local clinic will extend its hours this week to accommodate more patients.", "label": "Non-Misleading", "note": "routine service announcement"},
    {"text": "Natapos na ang pagsasaayos ng kalsada sa aming baranggay, maayos na ang daloy ng trapiko.", "label": "Non-Misleading", "note": "routine infrastructure update"},
    {"text": "The weather bureau lifted the storm signal over the province this morning.", "label": "Non-Misleading", "note": "routine weather update"},

    # ---- Genuinely MISLEADING (false/fabricated claims, short, FB/video-transcript style) ----
    {"text": "BREAKING: Gobyerno daw magbibigay ng 100,000 pesos sa lahat ng Pilipino bukas, mag-claim na agad bago maubos!", "label": "Misleading", "note": "classic too-good-to-be-true giveaway scam"},
    {"text": "Scientists confirm that drinking bleach cures all viral infections within 24 hours.", "label": "Misleading", "note": "dangerous health misinformation"},
    {"text": "Ang bagong 5G towers ay nagdudulot ng cancer base sa sikretong estudyo ng gobyerno.", "label": "Misleading", "note": "debunked conspiracy claim"},
    {"text": "URGENT: Magsasara na raw ang lahat ng banko sa Pilipinas sa Lunes, kunin na agad lahat ng pera niyo.", "label": "Misleading", "note": "panic-inducing financial hoax"},
    {"text": "Isang senador umano ay inaresto kagabi dahil sa smuggling, pero wala pang opisyal na kumpirmasyon.", "label": "Misleading", "note": "unverified viral rumor framed as fact"},
    {"text": "A leaked document proves the moon landing in 1969 was entirely staged in a studio.", "label": "Misleading", "note": "well-known debunked conspiracy"},
    {"text": "Pwede raw mawala ang diabetes sa loob lang ng tatlong araw gamit itong isang halamang gamot.", "label": "Misleading", "note": "false miracle-cure health claim"},
    {"text": "Report says the president secretly resigned last night; mainstream media hiding the truth.", "label": "Misleading", "note": "fabricated political claim"},
    {"text": "Lahat ng cellphone load ngayong buwan ay ide-double umano ng mga telco bilang promo, i-forward sa lahat.", "label": "Misleading", "note": "classic forward-chain hoax"},
    {"text": "New study reveals vaccines contain microchips that track your location at all times.", "label": "Misleading", "note": "debunked anti-vaccine conspiracy"},
    {"text": "Sinabi ng isang artista na ang mga pagkaing may MSG ay nagiging dahilan ng pagkabulag.", "label": "Misleading", "note": "false celebrity-attributed health claim"},
    {"text": "Confirmed: the earth will experience 6 days of total darkness next week according to NASA.", "label": "Misleading", "note": "recurring viral hoax, falsely attributed to NASA"},
    {"text": "Libre na raw ang koryente sa buong bansa simula sa susunod na buwan ayon sa bagong batas.", "label": "Misleading", "note": "fabricated policy claim"},
    {"text": "Doctors warn that a popular instant noodle brand causes organ failure within a year of regular eating.", "label": "Misleading", "note": "false, unverified health scare"},
    {"text": "Isang pamilya umano ang namatay dahil sa bagong sakit na kumakalat sa isang partikular na palengke, i-share agad.", "label": "Misleading", "note": "unverified alarming health rumor"},
    {"text": "Government officials secretly admit the national ID system was designed for mass surveillance of citizens.", "label": "Misleading", "note": "unverified conspiracy claim"},
    {"text": "Pwede raw ma-cure ang COVID sa pag-inom lang ng mainit na tubig na may asin tuwing umaga.", "label": "Misleading", "note": "false pandemic-era health claim"},
    {"text": "Viral post claims a well-known bank is shutting down all branches permanently this week.", "label": "Misleading", "note": "unverified alarming financial rumor"},
    {"text": "Isang grupo umano ng mga pulitiko ang nagplano ng kudeta ngayong linggo base sa hindi nakikilalang insider.", "label": "Misleading", "note": "unverified political conspiracy"},
    {"text": "A chain message claims that answering a call from a specific number will instantly drain your bank account.", "label": "Misleading", "note": "classic tech-scare chain hoax"},
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE.parent / "docs/SHORT-STATEMENT-BIAS-PROBE.json")
    args = parser.parse_args()

    health = runtime.initialize()
    if not health["ready"]:
        raise SystemExit(health["error"])

    rows = []
    tn = fp = fn = tp = 0
    for item in PROBE_SET:
        prediction = runtime.predict(item["text"])
        truth_positive = item["label"] == "Misleading"
        predicted_positive = prediction.internal_label == "Misleading"
        if truth_positive and predicted_positive:
            tp += 1
        elif truth_positive and not predicted_positive:
            fn += 1
        elif not truth_positive and predicted_positive:
            fp += 1
        else:
            tn += 1
        rows.append({
            "ground_truth": item["label"],
            "note": item["note"],
            "predicted_label": prediction.internal_label,
            "public_label": prediction.public_label,
            "model_score": prediction.model_score,
            "correct": truth_positive == predicted_positive,
        })

    total = len(rows)
    accuracy = (tp + tn) / total if total else 0.0
    non_misleading_total = tn + fp
    misleading_total = tp + fn
    result = {
        "purpose": (
            "Read-only, hand-labeled, balanced probe of short/video-transcript-style "
            "statements. No training, tuning, or threshold change performed."
        ),
        "model": {key: health[key] for key in ("classifier", "training_run_id", "sha256", "decision_threshold")},
        "probe_size": total,
        "ground_truth_distribution": {"Non-Misleading": non_misleading_total, "Misleading": misleading_total},
        "confusion": {"TN": tn, "FP": fp, "FN": fn, "TP": tp},
        "accuracy": accuracy,
        "false_positive_rate_on_non_misleading": fp / non_misleading_total if non_misleading_total else None,
        "false_negative_rate_on_misleading": fn / misleading_total if misleading_total else None,
        "rows": rows,
        "interpretation_note": (
            "Unlike the earlier 10-item unlabeled probe, every statement here has a "
            "hand-assigned ground truth, so FP/TN here measure genuine bias toward the "
            "Misleading class on short inputs, not just a count of Misleading outputs."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
