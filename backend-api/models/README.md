# Pinned hybrid artifacts and local trial

The stable rollback profile uses only `TRAINING RESULTS/models/model_4.joblib` from
run `20261011T235112Z`. The prepared workstation's local-trial profile uses only
`local-trials/full-cleaned-20261023T022416Z/models/model_4_full_dataset_CANDIDATE.joblib`
from run `full-cleaned-20261023T022416Z`. Each profile uses its own saved encoder,
Tagalog tokenizer, feature configuration, scalers and metadata. Keep every supplied
file unchanged.

See [the candidate trial guide](../../docs/LOCAL-CANDIDATE-TRIAL.md) and
[the integration guide](../../docs/HYBRID-INTEGRATION.md) for the full layout,
hashes, versions, inference contract and raw-text comparison results.

The entire training results directory is ignored by Git. Do not copy model binaries,
records, the embedding cache or secrets into public frontend assets. Production
Compose mounts only the required inference components, read-only. The old
`hybrid_model.pkl`/schema-1 bundle and alternative model files are not supported.
