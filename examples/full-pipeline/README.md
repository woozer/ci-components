# Optional full pipeline example

This future-work example includes modules from `modules/todo/`. It is not part of the active Java demo and needs its scanner/signing services and policies before use.

This example combines Maven, npm, scanners, signing and production promotion. Start with the [hello-world demo](../../README.md) instead when learning the modules.

`application.gitlab-ci.yml` owns the job graph. `profile.yml` selects the modules and passes defaults. Read [setup](../../docs/setup.md) and [profile configuration](../../docs/organization-profile.md) before adapting it. The extra services and credentials are not configured by the hello-world sample.
