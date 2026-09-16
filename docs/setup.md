# Platformvoorwaarden voor de bibliotheek

Deze pagina is voor het platformteam. De [modulehandleiding](modules.md) bevat de projectvoorwaarden en benodigde tooling per actieve module. Voor installatie van de lokale demo gebruik je [installation.md](../installation.md); voor eigen adressen, credentials en OpenShift de [organisatiehandleiding](real-environment.md).

## Actieve modules beschikbaar maken

1. Publiceer de bibliotheek op dezelfde GitLab-instance als de afnemers en bescherm de uitgebrachte [componentversies](component-versions.md).
2. Lever goedgekeurde images en geschikte runners volgens [image en runner](modules.md#image-en-runner) en de voorwaarden bij iedere module. Regel CA-certificaten, netwerktoegang, proxies en registry-authenticatie.
3. Beheer credentials via passend beschermde GitLab-variabelen of een secretmanager. De lokale namen en toewijzingen staan bij [organisatie-instellingen](defaults.md). Het opnemen van een module richt geen serverrechten in.
4. Richt SonarQube en de Dependency-Check-feed in volgens de [scanhandleiding](scanners.md). Beheer de quality gate en het uitzonderingsbeleid centraal.
5. Lever Kubernetes- of OpenShift-toegang met beperkte namespace-rechten. Stel release- en deploymentrechten in volgens het [releasebeleid](releases.md). De beschikbare goedkeuringsfuncties hangen af van de GitLab-editie.
6. Valideer de inrichting met de [uitvoerbare samples](../examples/samples/README.md). De YAML- en contracttests alleen bewijzen geen werkende verbinding met scanners, registries of clusters.

De validatiejob van de componentbibliotheek gebruikt `CI_VALIDATION_IMAGE` met Python 3, Ruby's standaard YAML-library, Git en `sh`. Afnemers hebben deze testimage niet nodig om modules te gebruiken.

## Voorbereiding voor TODO-modules

De volgende inrichting hoort bij het toekomstige [uitgebreide profiel](organization-profile.md). Geen van deze zes modules draait al in de demo. Hun beoogde outputs staan in het [onderhoudsnaslagwerk](reference.md#modules-voor-toekomstig-gebruik); het [statusoverzicht](modules.md#todo-nog-niet-actief) beschrijft wat nog moet worden gevalideerd.

| Module | Voorbereidende inrichting |
|---|---|
| `npm-audit` | Node/npm-image, bereikbare auditdienst en beleid voor ernstgrenzen en uitzonderingen |
| `fortify` | Gekozen editie/licentie, scanner, client, taaltooling en Python 3; valideer de [scan- en beleidsadapter](fortify-adapters.md) met beperkte credentials |
| `image-scan` | Trivy-image, registry-toegang en actuele kwetsbaarheidsdatabase; de module maakt een scanrapport en CycloneDX-SBOM en controleert HIGH/CRITICAL |
| `image-sign` | Cosign-image, beheerde signing-identiteit of sleutel, `COSIGN_KEY_URI` en bijpassende KMS- en transparantielogafspraken |
| `image-verify` | Cosign-image, `COSIGN_PUBLIC_KEY` en expliciet vertrouwensbeleid; test geldige, ontbrekende en ongeldige handtekeningen |
| `zap-baseline` | Image met `zap-baseline.py`, schrijfbare `/zap/wrk`, bereikbare testomgeving en een beoordeeld `ci/zap/rules.tsv` |

Deze images hebben ook de [gedeelde shelltools](modules.md#image-en-runner) nodig. Geef scanner-, signing- en deploymentjobs alleen de credentials die zij gebruiken. Registry-authenticatie kan via de ondersteunde toolconfiguratie of een [componenthook](modules.md#kleine-aanvulling-binnen-een-component).

Trivy maakt in de TODO-module het volledige JSON-rapport, converteert dat naar CycloneDX en toetst daarna de ernstgrens. ZAP baseline voert een beperkte passieve scan uit; onze TODO-module blokkeert op exitcodes 1, 2 en 3. Deze beleidskeuzes vervangen geen volledige applicatiebeveiligingstest. Zie [Trivy-rapportconversie](https://trivy.dev/docs/latest/configuration/reporting/#converting) en [ZAP baseline](https://www.zaproxy.org/docs/docker/baseline-scan/).

## Omgevingen en releasebewijs

Gebruik voor onafhankelijke validaties aparte testnamespaces of houd een gedeelde omgeving bezet tijdens deployment én integratietests. Een resourcegroep alleen op de deploymentjob beschermt de volgende testjobs niet. De afwegingen staan bij [deploymentvolgorde](deployment-concurrency.md).

Richt opruimen en verloop van tijdelijke omgevingen in. Pas de bewaartermijn van jobartifacts aan wanneer releasebewijs langer beschikbaar moet blijven. Productiepromotie hoort dezelfde gevalideerde image-digest te gebruiken; eventuele handtekeningcontrole bij clustertoelating wordt buiten deze CI-modules ingericht.
