# Uitgebreid voorbeeld voor toekomstig gebruik

Dit voorbeeld gebruikt modules uit `modules/todo/`. Het hoort niet bij de actieve Java-demo. Richt eerst de benodigde scan-/signingdiensten en het bijbehorende beleid in.

Het voorbeeld combineert Maven, npm, scanners, signing en promotie naar productie. Begin voor het leren gebruiken van modules met de [uitvoerbare samples](../samples/README.md).

`application.gitlab-ci.yml` bepaalt de jobafhankelijkheden. `profile.yml` kiest de modules en geeft standaardwaarden door. De applicatie-YAML heeft instellingen onder `include:inputs`, maar definieert geen keuzevelden voor **New pipeline**. Lees [inrichting](../../docs/setup.md) en [profielconfiguratie](../../docs/organization-profile.md) voordat je het voorbeeld aanpast. De extra diensten en credentials worden niet door de hello-world-sample ingericht.
