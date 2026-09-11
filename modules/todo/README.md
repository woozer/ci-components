# Modules for future work

These modules are not used by the current Java demo. They are retained for future evaluation; scanner services, policies and other integrations may still need implementation or live validation.

The active modules are in [templates/](../../templates/). The [broader pipeline example](../../examples/full-pipeline/) explicitly references these TODO files for illustration. Contract checks continue to cover their YAML and scripts, but do not establish production readiness.

Before activating one, identify a real consumer, evaluate supported GitLab/vendor implementations, validate its service integration and then move the selected implementation into `templates/`. Keep the public inputs, outputs and failure behavior explicit. See [reuse and standards](../../docs/reuse-and-standards.md).
