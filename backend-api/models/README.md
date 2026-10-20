# Pinned hybrid artifacts

The active runtime uses only `TRAINING RESULTS/models/model_4.joblib` from run
`20261011T235112Z`, plus its saved encoder folder, Tagalog tokenizer, feature
configuration and `run_manifest.json`. Keep the supplied files unchanged.

See [the integration guide](../../docs/HYBRID-INTEGRATION.md) for the full layout,
hashes, versions, inference contract and raw-text comparison results.

The entire training results directory is ignored by Git. Do not copy model binaries,
records, the embedding cache or secrets into public frontend assets. Production
Compose mounts only the required inference components, read-only. The old
`hybrid_model.pkl`/schema-1 bundle and alternative model files are not supported.
