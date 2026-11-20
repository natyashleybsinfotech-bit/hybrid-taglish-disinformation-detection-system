"""Keep regression tests independent of private laptop configuration."""
import os

# Tests declare their own trial settings using scoped patches. Never read live
# API credentials, database accounts, quotas or experimental policy from .env.
os.environ['SURI_LOAD_ENV_FILES'] = 'false'

# Unit tests use explicit local-reader fixtures; live calibration is separate.
os.environ['SURI_LOCAL_NLI_ENABLED'] = 'false'
