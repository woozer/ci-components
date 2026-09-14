# Componentversies

Afnemers gebruiken een volledige versie zoals `1.0.0`. Die Git-tag wijst naar één geteste commit van `root/ci-components`. Alle componenten, gedeelde configuratie, voorbeelden en de centrale pipeline in deze repository krijgen samen dezelfde versie. Dit volgt [GitLabs componentmodel](https://docs.gitlab.com/ci/components/#component-versions).

Voor één module:

```yaml
include:
  - component: $CI_SERVER_FQDN/root/ci-components/maven-build@1.0.0
    inputs:
      image: $JAVA_CI_IMAGE
```

Voor `include:project` gebruik je `ref: '1.0.0'`. Geef dezelfde versie door als `library-ref` wanneer het opgenomen voorbeeld of de standaardpipeline dat vraagt. Het formulier in `spec:include` moet ook die versie gebruiken. Containerimages blijven centraal vastgezet op digest; een componentversie en een applicatierelease zijn afzonderlijke versies.

De platformbeheerder publiceert na geslaagde moduletests en samplepipelines een nieuwe tag op een beoordeelde commit van `main`. We beginnen met `1.0.0` en volgen [Semantic Versioning](https://semver.org/lang/nl/): een patch voor compatibele fixes, een minor voor compatibele uitbreidingen en een major voor brekende wijzigingen. Een bestaande versie wordt niet verplaatst, verwijderd of opnieuw gebruikt. Afnemers kiezen een upgrade via hun eigen merge request.

[Protected tags](https://docs.gitlab.com/user/project/protected_tags/) beperken het aanmaken van versietags tot bevoegde beheerders en blokkeren overschrijven via Git. Ze controleren op zichzelf niet of een commit van `main` komt. Die herkomst en de groene validatie controleren we bij publicatie. Beheerders kunnen beschermde tags nog via GitLab verwijderen; het verbod daarop is aanvullend organisatiebeleid, geen absolute technische onveranderlijkheid.

Tijdens ontwikkeling test de componentpipeline de exacte `CI_COMMIT_SHA`. Zo testen we de wijziging vóórdat zij een versienummer krijgt. Volledige hashes blijven daarom toegestaan voor kandidaatvalidatie. Gebruik voor dagelijkse afname een uitgebrachte versie; `main`, `latest` en gedeeltelijke versies zoals `1` schuiven mee en zijn hier niet de gekozen aanpak. Publicatie in de CI/CD Catalog is niet nodig voor volledige Git-tags en is nog niet ingericht.

## Overstappen op 2.0.0

`maven-build` voert voortaan ook de unittests uit. Een mislukte unittest blokkeert de build. Publicatie slaat die tests over; Cucumber blijft de afzonderlijke integratiestap.

`release-reserve` en `java-service.yml` kiezen automatische patches binnen `release-line`, standaard `0.1`. Gebruik bij een bestaande reeks, bijvoorbeeld `2.3`, de input `release-line: "2.3"` in de projectconfiguratie. De vorige automatische selectie van de hoogste versie over alle reeksen vervalt. Een handmatig releasenummer moet binnen de ingestelde reeks vallen. Deze gewijzigde defaults zijn de reden voor een nieuwe majorversie van de componentbibliotheek. De bibliotheekversie en de releaseversie van een applicatie zijn onafhankelijk.
