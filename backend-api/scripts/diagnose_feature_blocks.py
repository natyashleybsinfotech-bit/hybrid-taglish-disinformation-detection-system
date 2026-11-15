"""Offline feature-block intervention; never trains or changes the serving model.

Synthetic statements are diagnostic inputs, NOT evidence-verified truth labels.
Padding changes embeddings AND ratios. Block interventions isolate the numeric
contribution of each block using its saved training mean (standardized zero).
Those artificial interventions are not deployable predictions or causal proof.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from src.model_runtime import ModelRuntime, PROFILES
from src.hybrid_pipeline import FEATURE_NAMES, prepare_text

INPUTS = [
    "Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration.",
    "Bukas magsisimula na ang klase sa mga paaralang naka-set sa August 1 schedule.",
    "Read the full article before sharing. Check the original source.",
    "P1.4B WORTH OF ILLICIT VAPE PRODUCTS SEIZED The Bureau of Customs seized more than P1.4 billion worth of illicit vape products.",
    "BREAKING: Gobyerno daw magbibigay ng 100,000 pesos sa lahat ng Pilipino bukas, mag-claim na agad bago maubos!",
    "Confirmed: the earth will experience 6 days of total darkness next week according to NASA.",
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Explicit root avoids the current serving profile's configured root.
    runtime = ModelRuntime(root=BASE / PROFILES[args.profile]['artifact_directory'], profile_id=args.profile)
    health = runtime.initialize()
    if not health['ready']:
        raise SystemExit(health['error'])
    pipeline = runtime._pipeline
    texts, variants = [], []
    for i, text in enumerate(INPUTS):
        for name, value in [('original', text), ('repeat_same_text_8', ' '.join([text] * 8)),
                            ('added_neutral_sentences', text + ' Please read the complete statement. This paragraph provides additional wording for a diagnostic comparison. The original statement remains above. ' * 4)]:
            variants.append((i, name))
            texts.append(prepare_text(value))
    embeddings, chunks, tokens = pipeline.embed_texts(texts)
    linguistic = np.vstack([pipeline.linguistic_features(text) for text in texts])
    context = pipeline.bundle['context_scaler'].transform(embeddings)
    language = pipeline.bundle['ling_scaler'].transform(linguistic)
    matrix = np.hstack([context, language])
    classifier = pipeline.bundle['classifier']
    positive = list(classifier.classes_).index(1)
    assert list(classifier.classes_) == [0, 1]
    weights = classifier.coef_[0]
    intercept = float(classifier.intercept_[0])
    contextual_logit = context @ weights[:768]
    linguistic_logit = language @ weights[768:]
    full_logits = contextual_logit + linguistic_logit + intercept
    np.testing.assert_allclose(full_logits, classifier.decision_function(matrix), rtol=1e-6, atol=1e-6)
    probabilities = classifier.predict_proba(matrix)[:, positive]
    context_only = classifier.predict_proba(np.hstack([context, np.zeros_like(language)]))[:, positive]
    language_only = classifier.predict_proba(np.hstack([np.zeros_like(context), language]))[:, positive]
    rows = []
    for i, (case, variant) in enumerate(variants):
        rows.append({'case': case, 'variant': variant, 'text': texts[i],
            'words': len(texts[i].split()), 'content_tokens': int(tokens[i]), 'chunks': int(chunks[i]),
            'p_misleading': float(probabilities[i]),
            'decision': 'Misleading' if probabilities[i] >= health['decision_threshold'] else 'Non-Misleading',
            'context_logit': float(contextual_logit[i]), 'linguistic_logit': float(linguistic_logit[i]),
            'intercept': intercept, 'total_logit': float(full_logits[i]),
            'diagnostic_p_with_linguistic_at_training_mean': float(context_only[i]),
            'diagnostic_p_with_context_at_training_mean': float(language_only[i]),
            'linguistic_features': dict(zip(FEATURE_NAMES, map(float, linguistic[i]))),
            'per_linguistic_logit': dict(zip(FEATURE_NAMES, map(float, language[i] * weights[768:]))),
        })
    report = {'profile': args.profile, 'sha256': health['sha256'], 'threshold': health['decision_threshold'],
        'training_performed': False, 'production_changed': False,
        'ground_truth_verified': False, 'accuracy_claimed': False,
        'limitations': 'Synthetic probes; block replacement is an artificial off-distribution intervention. Padding alone cannot isolate linguistic ratios. No factual correctness inferred.',
        'rows': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    for row in rows:
        if row['variant'] == 'original':
            print(json.dumps({key: row[key] for key in ['case', 'p_misleading', 'context_logit', 'linguistic_logit', 'diagnostic_p_with_linguistic_at_training_mean']}), flush=True)
    print('Saved', args.output)

if __name__ == '__main__':
    main()
