# De demo installeren

Met deze inrichting bouw je een nieuwe lokale demo op vanuit een Git-checkout. Het startscript gebruikt Docker Compose en de beheer-API's van de diensten. Wachtwoorden en sleutels worden lokaal gegenereerd en bij volgende uitvoeringen hergebruikt.

## Eenmalig voorbereiden

Deze stappen zijn bedoeld voor een nieuwe Mac met Docker Desktop. Als Docker Desktop al is geïnstalleerd, open het dan en controleer de instellingen hieronder. Anders volg je eerst de [Docker-installatie voor Mac](https://docs.docker.com/desktop/setup/install/mac-install/).

Controleer in Terminal of Git beschikbaar is:

```sh
git --version
```

Ontbreekt Git, installeer dan de [Apple Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools) en rond het installatievenster af voordat je verdergaat:

```sh
xcode-select --install
```

Stel Docker Desktop als volgt in:

| Instelling | Waarde voor deze demo |
|---|---|
| Settings → Resources → Memory limit | 16 GB; onze geteste Mac heeft 32 GB RAM |
| Settings → General → Use containerd for pulling and storing images | Ingeschakeld |
| Kubernetes → Create cluster | Kies **kind** met één node en wacht tot het cluster gereed is |
| Settings → Advanced → Allow the default Docker socket to be used | Ingeschakeld; de installer gebruikt `/var/run/docker.sock` |

Zie [Docker Desktop-instellingen](https://docs.docker.com/desktop/settings-and-maintenance/settings/), [Kubernetes aanmaken](https://docs.docker.com/desktop/use-desktop/kubernetes/) en [de standaard Docker-socket](https://docs.docker.com/desktop/setup/install/mac-permission-requirements/#installing-symlinks). Laat de Mac wakker tijdens installatie en CI-runs.

De installer herkent Apple Silicon (`arm64`) en Intel (`amd64`) automatisch aan de Docker-daemon. Je hoeft geen aparte installatievariant te kiezen. De CI-images worden voor die architectuur gebouwd; ook de GitLab Runner-helper wordt daarop afgestemd.

De gebruikte basisimages bieden beide architecturen aan. De lokale uitvoering wordt hier op Apple Silicon gecontroleerd; een volledige installatie op een fysieke Intel-machine is nog niet uitgevoerd. Deze installer verwacht Docker Desktop met het ingebouwde kind-cluster; een losse Linux-Docker-installatie is nog geen gelijkwaardig ondersteunde variant.

De lokale registry gebruikt HTTP. Voeg onder **Settings → Docker Engine** de onderstaande instelling toe aan de bestaande JSON. Behoud de overige instellingen en eventuele bestaande registry-adressen en kies **Apply & restart**:

```json
{
  "insecure-registries": [
    "localhost:8082",
    "host.docker.internal:8082"
  ]
}
```

Zie [de registry-instellingen](infra/artifactory/README.md#docker-transport-en-bestaande-mirrors).

De beheertools draaien in een container. Python, Java, Maven en Node hoeven daarvoor niet op de Mac te worden geïnstalleerd. Internettoegang is nodig om images en dependencies op te halen.

## Starten vanuit Git

Haal de openbare componentbibliotheek en de gekoppelde pipeline- en applicatierepositories op. Voer daarna vanuit de hoofdmap het startscript uit:

```sh
git clone --recurse-submodules https://github.com/woozer/ci-components.git
cd ci-components
./infra/setup.sh check
./infra/setup.sh install
```

Het script richt de lokale GitLab CE, Artifactory JCR, SonarQube Community Build, runners en Kubernetes-toegang in. De Git-submodule `pipelines/` verwijst naar `ci-pipelines`; `java/` verwijst naar `hello-world`; `infra/seed/ci-samples/` verwijst naar de volledige repository `ci-samples`. De installer neemt de vastgelegde commits en hun geschiedenis over naar de gelijknamige projecten in een nieuwe GitLab. Bestaande repositories en releases worden behouden.

Artifactory JCR vereist acceptatie van de licentievoorwaarden. Het script mag die keuze niet stilzwijgend maken. De installatie beschrijft hoe je de voorwaarden bekijkt en na akkoord verdergaat met `--accept-jcr-eula`.

Als de installer daarop stopt, open dan de voorwaarden op je Mac:

```sh
open infra/artifactory/eula.html
```

Hervat na het lezen en je akkoord:

```sh
./infra/setup.sh install --accept-jcr-eula
./infra/setup.sh status
./infra/setup.sh verify
```

`verify` start de applicatiepipeline en daarna alle actieve samples. De links naar de pipelines verschijnen in de terminal. Deze controle kan geruime tijd duren doordat de lokale runner één job tegelijk uitvoert. Een mislukte pipeline laat de controle falen. In `infra/.state/verification.json` staan alleen de geslaagde resultaten van die controle.

Log in GitLab in als `root`. Het initiële wachtwoord staat in `infra/gitlab-ce/secrets/initial_root_password`. De beheerderscredentials voor Artifactory en SonarQube staan in hun eigen `secrets/credentials.json`. Het script toont de bestandslocaties en schrijft de wachtwoorden niet naar de terminal.

## Waar staan de gegenereerde geheimen?

De onderstaande paden zijn relatief aan de hoofdmap van je checkout. De installer maakt deze bestanden lokaal aan en hergebruikt ze bij een volgende uitvoering. Ze staan niet in Git en worden niet meegeleverd door een clone.

| Dienst of doel | Lokale bestanden |
|---|---|
| Eerste GitLab-login als `root` | `infra/gitlab-ce/secrets/initial_root_password`. Dit is het **initiële** wachtwoord; na een handmatige wijziging is dit bestand geen registratie van je nieuwe wachtwoord. |
| GitLab-beheer door de installer | `infra/gitlab-ce/secrets/provisioning-token` bevat de API-token. `setup-key` in dezelfde map is de private SSH-sleutel waarmee de installer repositories vult. |
| Artifactory-accounts | `infra/artifactory/secrets/credentials.json` bevat de gegenereerde beheer-, lees- en publicatieaccounts. |
| Artifactory-toegang vanuit Docker en Maven | `infra/artifactory/secrets/docker-read.json`, `docker-publisher/config.json`, `maven-settings.xml` en `publisher-password`. Dit zijn afgeleide inlogbestanden voor dezelfde lokale inrichting. |
| Artifactory-database | `infra/artifactory/.env` bevat `ARTIFACTORY_DB_PASSWORD`. |
| GitLab Runners | `infra/gitlab-runner/secrets/runner.json` en de overige `*-runner.json` bevatten runnerregistraties met authenticatietokens. De actieve runnerconfiguratie met tokens staat in `infra/gitlab-runner/secrets/config/config.toml`. |
| Kubernetes-toegang voor CI | `infra/gitlab-runner/secrets/kubeconfig.json` en `samples-kubeconfig.json` bevatten de verbinding en serviceaccounttoken voor respectievelijk de applicatie en samples. |
| Applicatie- en samplereleases | `infra/gitlab-runner/secrets/release-deploy-key` en `samples-release-key` zijn private SSH-sleutels voor releasetags. `release-registry.json` en `samples-registry.json` bevatten de bijbehorende registry-accounts. |
| SonarQube-accounts en database | `infra/sonarqube/secrets/credentials.json` bevat de gegenereerde accounts en het databasewachtwoord. `infra/sonarqube/.env` levert onder meer `SONAR_DB_PASSWORD` aan Compose. |
| SonarQube-analyse vanuit CI | `infra/sonarqube/secrets/gitlab-analysis-token` en `samples-analysis-token` bevatten de afzonderlijke analysetokens. |

Bestanden zoals `project.json`, `*-project.json`, `known_hosts` en `*.pub` zijn lokale metadata of openbare sleutels. Niet ieder bestand onder `secrets/` is dus zelf een geheim. GitLab krijgt daarnaast de benodigde CI-variabelen via de API; die staan bij **Settings → CI/CD → Variables** van het betreffende project, deels als bestandsvariabele en deels met een omgevingsscope.

De diensten bewaren ook eigen encryptiesleutels in hun Docker-volumes. GitLabs `/etc/gitlab/gitlab-secrets.json` hoort bij het Compose-volume `config`; Artifactory bewaart eigen beveiligingssleutels in zijn `data`-volume. De bestanden onder `infra/` alleen zijn daarom geen volledige back-up van een bestaande installatie.

Voor een **nieuwe, lege installatie** hoef je deze geheimen niet over te zetten: de installer genereert nieuwe waarden. Voor het **behouden van de bestaande installatie** bewaar je de lokale geheime bestanden samen met de databases, volumes en encryptiesleutels volgens de herstelprocedure. Commit deze bestanden niet in de openbare repositories. Zie [opnieuw installeren of verhuizen](#opnieuw-installeren-of-verhuizen).

## Wat staat in Git?

Git bevat Compose-bestanden, scripts, Dockerfiles en de broncode voor het vullen van een nieuwe demo. `.env`, `secrets/`, `infra/.state/` en gegenereerde lokale imageverwijzingen worden genegeerd. Controleer deze uitsluitingen voordat je de repository naar een externe Git-server pusht.

De broncode wordt beheerd in vier afzonderlijke repositories: [ci-components](https://github.com/woozer/ci-components), [ci-pipelines](https://github.com/woozer/ci-pipelines), [hello-world](https://github.com/woozer/hello-world) en [ci-samples](https://github.com/woozer/ci-samples). De componentbibliotheek bewaart alleen de Git-submoduleverwijzingen naar de pipeline- en applicatierepositories. Zo kan één recursieve checkout de volledige demo vullen zonder verbinding met de oude lokale GitLab.

Heb je al gecloned zonder `--recurse-submodules`, haal dan de vastgelegde submodulecommits alsnog op:

```sh
git submodule update --init --recursive
```

Voer dit commando ook uit na een update van de componentbibliotheek. De installer controleert of alle drie submodules beschikbaar zijn op de vastgelegde commit. Gebruik voor installatie de actuele `main`; de benodigde tags staan in `infra/seed/manifest.json`.

Neem bij het overzetten naar een externe remote ook de componenttags `1.0.0` en `1.2.0` en de tag `1.0.0` van **ci-pipelines** mee. De applicatie gebruikt de pipelineversie; de pipeline zet haar moduleversies zelf vast. `check` controleert of de tags lokaal beschikbaar zijn. Nieuwe GitLab-projecten worden alleen gevuld als hun repository leeg is; bestaande branchgeschiedenis wordt niet vervangen.

## Opnieuw installeren of verhuizen

Een nieuwe installatie genereert eigen credentials en begint met lege databases. Een herstart hergebruikt de opgeslagen credentials en Docker-volumes. Nieuwe wachtwoorden vervangen geen bestaande encryptiesleutels.

Voor een test met lege demodatabases commit je eerst de broncode. Bekijk daarna de resetdoelen:

```sh
./infra/setup.sh reset
```

Dit toont alleen wat zou worden verwijderd. Met `./infra/setup.sh reset --delete-data` verwijder je daadwerkelijk de vier demostacks met hun volumes, de twee demonamespaces en de gegenereerde lokale credentials. Daarna voer je `install` en `verify` opnieuw uit. De Git-repository en applicatiebroncode blijven staan. Ook het Docker Desktop-cluster en niet bij de demo behorende workloads blijven behouden; er wordt geen globale `docker system prune` uitgevoerd.

Een **volledige Docker-wipe** gaat verder dan deze demoreset: die verwijdert ook containers, benoemde volumes, databases, images en buildcache van andere projecten. Inventariseer die eerst met `docker ps -a` en `docker volume ls`. Docker Desktops Kubernetes-cluster bevat daarnaast eigen workloads en data; een ondersteunde clusterreset is `docker desktop kubernetes reset-cluster`. Zie [Docker Desktop Kubernetes](https://docs.docker.com/desktop/use-desktop/kubernetes/). Een globale wipe hoort daarom niet in de standaardinstaller. Bewaar de Git-checkout en tags buiten Docker en verwijder bij een verse demo ook de gegenereerde credentials via de demoreset.

Wil je de huidige gebruikers, merge requests, artifacts en scanresultaten behouden, dan moet je ook de opgeslagen gegevens verhuizen. Die staan in Docker-volumes, buiten `infra/`. Zie [Docker-back-ups](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/) en [GitLab herstellen](https://docs.gitlab.com/administration/backup_restore/restore_gitlab/). Voor GitLab zijn dezelfde versie, dezelfde editie en de oorspronkelijke encryptiesleutels nodig.

## Lokale adressen

De installer registreert `ci-components` en `ci-pipelines` als afzonderlijke catalogusprojecten. Op een lege installatie ontbreken nog de GitLab-releases, ook als de broncodetags al zijn overgezet. Open bij **ci-components → Build → Pipelines → New pipeline** de tag `1.2.0` en start de pipeline. Na de contracttests, alle samples en **publish-catalog** verschijnt deze versie in de [lokale CI/CD Catalog](http://localhost:8929/explore/catalog). Voer daarna bij **ci-pipelines** hetzelfde uit voor de tag `1.0.0`; die pipeline valideert de standaardpipeline in **ci-samples** en publiceert `java-service`. Doe dit alleen als die catalogusreleases nog niet bestaan; bestaande versies blijven behouden. Zie [cataloguspublicatie](docs/component-versions.md#publicatie-in-de-cicd-catalog).

| Dienst | Adres |
|---|---|
| GitLab | <http://localhost:8929> |
| Artifactory | <http://localhost:8082> |
| SonarQube | <http://localhost:9000> |

HTTP en vaste localhost-poorten zijn keuzes voor deze lokale demo. De inrichting maakt geen verbinding met de servers van de organisatie.

Voor gebruik van de modules met bestaande organisatiediensten en OpenShift, zie [gebruik in de eigen organisatie](docs/real-environment.md). Daar horen eigen organisatie-instellingen en beheerde credentials bij; de lokale demo-installer vervangt die diensten niet.
