#!/bin/sh
set -eu
printf 'Cleanup hook ran after job status %s\n' "$CI_JOB_STATUS"
# Clean up only resources owned by this job. Use environment expiry as a backstop.
