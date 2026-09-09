#!/bin/sh
set -eu
# Optional custom outputs must use the component's prefix plus CUSTOM_.
# CI_MODULE_EXTRA_OUTPUTS is provided to every hook; never write secrets here.
printf '%s_CUSTOM_BUILD_LABEL=%s\n' "$MODULE_OUTPUT_PREFIX" "$CI_COMMIT_SHORT_SHA" >> "$CI_MODULE_EXTRA_OUTPUTS"
