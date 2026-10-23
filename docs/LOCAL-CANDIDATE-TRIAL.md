# Full-cleaned candidate local trial

This workstation currently selects training run `full-cleaned-20261023T022416Z`
for local testing only. The candidate is not approved for public deployment, and
`config.validate_runtime_config()` rejects this profile when `SURI_APP_ENV=production`.

## Identity and contract

| Field | Active local value |
| --- | --- |
| Classifier | `model_4_full_dataset_CANDIDATE.joblib` |
| SHA-256 | `c2d7df1c519c4022c395a29e1d469e3089452fa8a9b6a15a2079eaa0216ea376` |
| Run ID | `full-cleaned-20261023T022416Z` |
| Saved threshold | `0.4000000000000001` |
| Labels | `0 = Non-Misleading`, `1 = Misleading` |
| Input width | 768 contextual + 7 linguistic = 775 |
| Local device | CPU |

The archive was extracted without overwriting existing files to the ignored directory
`backend-api/models/local-trials/full-cleaned-20261023T022416Z/`. Model binaries,
raw records, saved predictions, and the supplied caption regression text stay out of
Git and all frontend assets. The local regression text is stored under that ignored
artifact root; committed reports retain only case names, scores, counts, and hashes.

The loader verifies the classifier hash before unpickling. It also verifies every
encoder file hash, the feature configuration, Tagalog tokenizer hash, bundle structure,
scalers, class order, saved threshold, and runtime versions. The raw checkpoint is a
masked-language-model checkpoint; exactly these unused vocabulary-head keys are allowed:

- `vocab_transform.weight`
- `vocab_transform.bias`
- `vocab_layer_norm.weight`
- `vocab_layer_norm.bias`
- `vocab_projector.bias`

Any other missing, unexpected, mismatched, or erroneous key makes readiness false.
Inference manually builds `[CLS] + up to 510 content tokens + [SEP]` for each chunk,
excludes padding and those two added tokens from pooling, and computes a content-token
weighted mean over the complete text. It never truncates long text silently.

## Install and start

From the repository root on this prepared workstation:

```powershell
.\.venv\Scripts\python.exe -m venv .venv-candidate-20261023-isolated
.\.venv-candidate-20261023-isolated\Scripts\python.exe -m pip install -r backend-api\requirements-test-candidate.txt
```

The private `backend-api/.env.local` must contain this line and should not set an
artifact-root override:

```dotenv
SURI_MODEL_PROFILE=full-cleaned-20261023T022416Z
```

Start exactly one API process:

```powershell
.\scripts\start-mariadb.ps1
Set-Location backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m src.manage migrate
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Verify identity before using the extension:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready | ConvertTo-Json -Depth 8
```

The response must name the candidate classifier and run ID above, report the expected
hash, threshold `0.4000000000000001`, actual device, and `ready: true`. The fields
`local_trial: true` and `deployment_approved: false` are deliberate.

Build and reload the extension:

```powershell
Set-Location ..\chrome-extension
npm.cmd ci
npm.cmd run build
```

Open `chrome://extensions`, click **Reload** on SuriPH, then refresh every open Facebook
tab. Old content scripts remain in an already-open page until that page is refreshed.

## Verification

```powershell
Set-Location ..\backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
..\.venv-candidate-20261023-isolated\Scripts\python.exe scripts\verify_candidate_regressions.py
..\.venv-candidate-20261023-isolated\Scripts\python.exe scripts\verify_hybrid.py --output ..\docs\CANDIDATE-HYBRID-VERIFICATION.json
```

`verify_hybrid.py` hashes each raw text and joins it to the saved prediction by
`record_id`; it does not read cached embeddings or tune anything. CPU comparisons use
`atol=1e-5` and `rtol=1e-5`. The training runtime used CUDA (`torch 2.11.0+cu130`), while
this trial uses the CPU build of the same torch version. Transformers emits an upstream
tokenizer-regex warning for this saved tokenizer; changing that option would change the
recorded behavior, so the integration leaves it unchanged and relies on raw-text parity.

The complete local run checked all 3,470 saved test records: probability mismatches `0`,
label mismatches `0`, and maximum absolute probability difference
`5.340033791989551e-06`. Of those records, 1,646 required multiple chunks. The saved
references include 108 false positives and 114 false negatives against inherited labels.

The inherited-label test metrics in `results.json` are accuracy `0.9360230548`, macro
F1 `0.9002514109`, false-positive rate `0.0389750992`, and misleading recall
`0.8369098712`. These are agreement with inherited labels, not proof of factual truth.
The dataset is not an independently verified Facebook evaluation set and retains known
annotation conflicts.

## Explicit rollback

Stop the candidate API. Change only this line in `backend-api/.env.local`:

```dotenv
SURI_MODEL_PROFILE=20261011T235112Z
```

Then start the API with the original `.venv`, whose recorded Transformers and
scikit-learn versions match the rollback bundle:

```powershell
Set-Location backend-api
..\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Confirm `/ready` reports `model_4.joblib`, run `20261011T235112Z`, hash
`72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c`, and threshold
`0.65`. The runtime never rolls back automatically. If the selected profile fails, it
returns service unavailable and leaves readiness false.
