# Short-text retraining plan — 20 November 2026

Status: diagnostic plan only. No training, relabeling, threshold change or replacement of the active classifier was performed. Evidence-reader migration does not repair the DistilBERT-LR distribution problem.

## Observed input format

The specified `backend-api/models/TRAINING RESULTS/records/full_text_label.csv` is **not present** in this archived original run. Its actual dataset is `records/dataset_input.csv`, with exactly `topic,text,label`. `records/train.csv` has the same fields. `records/partitions.csv` has `record_id,claim_group_id,topic,label,split`.

The archived `SuriPH_Repaired_Training_Run.ipynb` reads `SuriPH_Final_Training_4000.csv`; checks exactly 4,000 records, eight topics and 250 rows per topic/class; maps `Non-Misleading` to 0 and `Misleading` to 1. Its exact record IDs are SHA-256 hashes of original UTF-8 text. Whitespace normalization is separate from this identity. The notebook and archived records remain unchanged.

## Proposed supplement

The researcher plans to prepare **120 short English/Taglish rows: 60 Misleading and 60 Non-Misleading**. That dataset has not been supplied in this migration. Use the original three-column textual schema (`topic,text,label`) and the existing eight topic names. Preserve exact original texts and supplied labels. Keep a separate provenance/review file with record hash, source, claim/event group, date, reviewer and reason for the label; do not silently infer factual labels from a high-confidence model output or a writing style.

Check blanks, exact/normalized duplicates, label conflicts, language, length, topic distribution and near-duplicate claims against **all existing partitions**, including historical validation and test records. A held-out claim or a paraphrase of it must not be appended to training. Group related events and paraphrases together; quarantine conflicts and uncertain labels. The existing bias probe contains intended/example labels rather than independently verified real events and is not proposed training data.

## Append versus a new split

For a reproducible comparison, preserve the entire original archive and partitions. Create a separate, versioned repaired-run notebook and run manifest only after explicit authorization. Do not append directly to the archived notebook's upload: its 4,000-row and topic-balance assertions would fail, and silently deleting those assertions would change the documented protocol.

The preferred comparison is **append approved, non-overlapping supplement rows to training only**, keeping old validation/test IDs and original test predictions frozen. Fit all learned components only on the new training partition; select hyperparameters and the model threshold on the declared validation data, never the test or live demo examples. Record any changed protocol assertions and both data hashes in the new notebook version. This would be a new experiment, not a replacement of the original results.

Because 120 training additions do not create an independent short-text test, collect a separate balanced, source-checked caption/transcript audit that was not used for data design, calibration or debugging. If instead the 120 rows are split into train/validation/test, decide and group that split **before** any fitting; there would then be fewer than 120 new training examples. Do not compare results from different partitions as though they were the same-test improvement.

Report the confusion matrix, per-class precision/recall, macro F1 and false-positive rate, broken down by length, language and input modality. Short balanced samples have wide uncertainty; no Gemini-equivalent or error-free claim follows from them. Use paired same-example comparisons for old/new predictions where appropriate, and retain failed runs as records.

## Researcher input still needed

Supply the actual 120-row data with provenance and reviewed labels, and explicitly authorize any future retraining. A separate representative real-post audit remains needed. No new training notebook or altered classifier is delivered by the local-reader migration.
