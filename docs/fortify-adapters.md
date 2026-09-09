# Fortify adapter contract

Fortify edition, version, licensing, endpoints, and organization policy are not specified yet. The two components therefore require explicit adapters and fail if those adapters are missing. This starter does not claim a working Fortify installation or substitute a successful no-op.

Supply the adapters in the consuming repository, or place an approved implementation in the component's dedicated image and use a repository script to invoke it. The scan image needs your Fortify scanner/client, appropriate language tooling, POSIX `sh`, and Python 3; the gate image only needs your policy client, `sh`, and Python 3. They can be different images.

The scan adapter is invoked from the component working directory:

```sh
sh ci/fortify/scan.sh \
  --receipt /absolute/output/scan.json \
  --commit COMMIT_SHA \
  --pipeline-id PIPELINE_ID
```

It must submit the current source, wait for processing to complete, and write a JSON receipt:

```json
{
  "schema_version": 1,
  "provider": "ssc",
  "scan_id": "immutable-scan-or-artifact-id",
  "application_version_id": "provider-specific-id",
  "commit_sha": "the-exact-CI_COMMIT_SHA",
  "pipeline_id": "the-exact-CI_PIPELINE_ID",
  "status": "completed"
}
```

The scan component validates commit, pipeline, completion status, and scan ID. Its output variable points to the receipt file. Credentials must not appear in the receipt.

The separate policy adapter is invoked as:

```sh
sh ci/fortify/gate.sh \
  --receipt /absolute/input/scan.json \
  --report /absolute/output/policy.json
```

It must evaluate the exact scan in the receipt against your approved policy and write:

```json
{
  "scan_id": "same-immutable-scan-or-artifact-id",
  "policy_version": "security-policy-2026-01",
  "status": "passed"
}
```

Return nonzero for policy violations, authentication/network errors, missing results, incomplete scans, or timeouts. A failed policy may still write its report for diagnostics. The gate component rejects a success report for the wrong scan.

For SSC policies that inspect the latest application-version state, isolate versions by pipeline/commit or serialize the entire upload, processing, and policy sequence. Locking only the upload job does not stop another pipeline changing the version before policy evaluation. Persist provider IDs and verify that the policy response belongs to the receipt. Do not silently assess whichever scan happens to be latest.

The official `fcli ssc action run ci` can orchestrate scan submission and completion. Its `check-policy` action is documented as a sample; customize and version the actual organization policy. Disable optional PR/MR comment publication in these adapters unless that behavior is explicitly wanted. For Fortify on Demand, use the corresponding FoD APIs/actions and translate their results into the same contract. [Fortify SSC actions](https://fortify.github.io/fcli/latest/ssc-actions.html)
