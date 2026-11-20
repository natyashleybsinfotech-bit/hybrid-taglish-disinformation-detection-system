"""Explicit public model download; request-time inference remains offline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from huggingface_hub import snapshot_download

if __name__ == '__main__':
    snapshot_download('MoritzLaurer/mDeBERTa-v3-base-mnli-xnli',
                      revision='8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c',
                      local_dir=str(config.LOCAL_NLI_MODEL_DIR), token=False,
                      allow_patterns=['config.json','model.safetensors','tokenizer.json',
                                      'tokenizer_config.json','special_tokens_map.json',
                                      'added_tokens.json','spm.model','README.md'])
    print('Pinned local NLI artifacts prepared. No submitted content was uploaded.')
