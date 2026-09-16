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

Tijdens ontwikkeling test de componentpipeline de exacte `CI_COMMIT_SHA`. Zo testen we de wijziging vóórdat zij een versienummer krijgt. Volledige hashes blijven daarom toegestaan voor kandidaatvalidatie. Gebruik voor dagelijkse afname een uitgebrachte versie; `main`, `latest` en gedeeltelijke versies zoals `1` schuiven mee en zijn hier niet de gekozen aanpak.

## Publicatie in de CI/CD Catalog

De vijftien actieve componenten worden samen gepubliceerd vanuit het project `root/ci-components`. Open [de lokale catalogus](http://localhost:8929/explore/catalog) en kies **ci-components** om versies, componenten en hun inputs te bekijken. GitHub bevat de openbare broncode; de cataloguspublicatie gebeurt op de GitLab-instance die de componenten uitvoert. Voor een catalogus op GitLab.com is een afzonderlijke publicatie daar nodig. De interne bestanden onder `shared/` en `pipelines/internal/` en de TODO-modules worden geen aparte cataloguscomponenten. De standaardpipeline blijft voorlopig beschikbaar als `include:project`.

Voor de eerste publicatie stelt de platformbeheerder bij **Settings → General → Visibility, project features, permissions** de optie **CI/CD Catalog project** in en vult een projectomschrijving in. De demo-installer doet dit via GitLabs GraphQL-API. Die instelling alleen maakt het project nog niet vindbaar; daarvoor moet een versie worden gepubliceerd.

Publiceer daarna een nieuwe versie als volgt:

1. Merge de beoordeelde wijziging naar protected `main`. Houd de Git-tags beschermd; hergebruik bestaande tags niet.
2. Maak een nieuwe tag zoals `1.1.0` op de gekozen commit van `main`. De tagpipeline voert de contracttests en alle negentien samples uit op precies die componentcommit.
3. Na geslaagde validatie controleert **publish-catalog** dat de commit op `main` voorkomt. GitLabs standaardveld `release:` maakt vervolgens de release en publiceert de componenten in de catalogus.

De bibliotheekpipeline vereist `CI_VALIDATION_IMAGE`, `CI_RELEASE_IMAGE` en `CI_SAMPLES_PROJECT`. De release-image bevat `glab` en Git; de lokale installer spiegelt de officiële, op digest vastgezette CLI-image naar Artifactory. Alleen in de lokale Docker-demo stelt hij ook `GITLAB_API_HOST=host.docker.internal:8929` in, zodat de CLI de API kan bereiken zonder de openbare browser-URL te wijzigen. De aanmelding gebruikt het tijdelijke `CI_JOB_TOKEN`; een aparte releasetoken is niet nodig.

Een tag buiten protected refs of een commit buiten `main` kan niet via deze publicatiejob worden uitgebracht. Dit is onze releaseafspraak boven op GitLabs catalogusfunctionaliteit. Een bestaande release opnieuw uitvoeren wordt geweigerd; maak voor gewijzigde componenten een nieuwe versie. De applicatiemodule `gitlab-release` blijft de Releases API gebruiken voor applicatiereleases. Cataloguspublicatie vereist juist `release:`. Zie [GitLabs publicatieprocedure](https://docs.gitlab.com/ci/components/#publish-a-component-project).

Versie `1.1.0` voegt de cataloguspublicatie en controles op outputconflicten toe. In de Java-strategie gebruiken de optionele test en de test na deployment voortaan respectievelijk `CUSTOM_TEST` en `DEV_CUCUMBER`; de gewone test behoudt `CUCUMBER_TEST`. Dit herstelt dubbele prefixes. Controleer eventuele eigen verwijzingen naar deze outputs vóór een upgrade. De bestaande tag `1.0.0` blijft intact.
