#!/bin/sh
set -eu
python3 - <<'PY'
import json, os, re
with open(os.environ['CI_MODULE_PARAMETERS_FILE']) as stream:
    parameters = json.load(stream)
if parameters.get('requireDigest', True):
    if not re.fullmatch(r'.+@sha256:[a-f0-9]{64}', os.environ['CI_HOOK_WORK']):
        raise SystemExit('An immutable image reference is required')
PY
# Insert your organization's additional work before requesting continuation.
"$CI_HOOK_NEXT" "$CI_HOOK_WORK"
