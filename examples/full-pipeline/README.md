# Optional full pipeline example

This example combines Maven, npm, scanners, signing and production promotion. Start with the [hello-world demo](../../README.md) instead when learning the modules.

`application.gitlab-ci.yml` owns the job graph. `profile.yml` selects the modules and passes defaults. Read [setup](../../docs/setup.md) and [profile configuration](../../docs/organization-profile.md) before adapting it. The extra services and credentials are not configured by the hello-world sample.
