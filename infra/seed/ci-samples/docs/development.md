# Java 25 Hello World

Een zelfstandige Maven-applicatie met Spring Boot 4.1.1, opgezet op 9 september 2026. Bouw en test met Java 25. Voor `verify` zijn GitLab CI-componenten, Docker en Artifactory niet nodig. De eerste build downloadt Maven en dependencies uit publieke repositories.

| Module | Verantwoordelijkheid |
|---|---|
| `hello-app` | Spring Boot-applicatie met `GET /hello`, dieren-API, health en Jib-configuratie |
| `integration-tests` | Cucumber-scenario's die echte HTTP-verzoeken uitvoeren en antwoorden controleren |

## Bouwen en testen

```sh
./mvnw verify
```

De wrapper is vastgezet met een checksum en vereist `unzip` op Unix. Een geïnstalleerde Maven 3.9.12 werkt ook met `mvn verify`. CI gebruikt Maven 3.9.12 uit de vaste containerimage.

Maven bouwt beide modules. Cucumber start de applicatie op een vrije loopbackpoort. De begroetingstest controleert `/hello` op status `200`, exact `hello world` en contenttype `text/plain`. De suite controleert ook health, dieren en een onbekend endpoint. Daarna stopt de applicatie. Maven Failsafe en de JUnit-suite falen als er geen tests worden gevonden. Gebruik `verify` voor integratietests; `test` en `package` stoppen vóór die fase.

Rapporten:

- `integration-tests/target/failsafe-reports/` — JUnit XML en Maven-resultaten.
- `integration-tests/target/cucumber/cucumber.html` — leesbaar Cucumber-rapport.
- `integration-tests/target/cucumber/cucumber.json` — gestructureerde resultaten.

## De applicatie starten

```sh
java -jar hello-app/target/hello-app-1.0.0-SNAPSHOT-exec.jar
```

Voer in een andere terminal uit:

```sh
curl http://localhost:8080/hello
# hello world
```

Geef voor een al draaiende applicatie of container de basis-URL mee. In deze modus starten en stoppen de tests geen applicatie:

```sh
./mvnw verify -Dcucumber.base-url=http://localhost:8080
```

## Een image bouwen met Jib

Jib is alleen ingesteld in `hello-app`. De backend heeft geen Dockerfile en `verify` publiceert geen image. De Compose-configuratie hieronder start backend én UI. Bouw daarom eerst ook de UI-image volgens [de UI-handleiding](#aparte-angular-deployable).

```sh
# Build into the local Docker daemon.
./mvnw -pl hello-app compile jib:dockerBuild

# Run the Jib image on localhost:8080.
docker compose up -d

# Run the same Cucumber scenario against the container.
./mvnw verify -Dcucumber.base-url=http://localhost:8080

# Stop the application container.
docker compose down
```

De image draait met UID/GID `10001:10001` op poort 8080. Voor deze machine is de standaardarchitectuur `arm64`. Gebruik `-Dcontainer.architecture=amd64` voor amd64. De standaardimagenaam is `hello-world:local`. Met `-Djib.to.image=...` en `-Djib.from.image=...` wijzig je de bestemming en de Java 25-runtime-image.

Maak een imagearchief zonder Docker-daemon of doelregistry:

```sh
./mvnw -pl hello-app compile jib:buildTar
# hello-app/target/jib-image.tar
```

Jib schrijft ook `hello-app/target/jib-image.digest`. Gebruik de digest voor promotie of deployment van een gepubliceerde image.

Lokale Artifactory wordt apart beheerd in `../infra/artifactory`. Deze bevat een lokale repository voor imagepublicatie. Er is geen verbinding met de Artifactory van de organisatie ingesteld.

## GitLab-pipeline

Project: <http://localhost:8929/root/hello-world>

Het [CI-bestand](../.gitlab-ci.yml) bevat de centrale strategie-include, het gedeelde formulier en applicatie-instellingen. Buildjobs, releasecontroles, registry-login en deploymentaansturing staan in de CI-bibliotheek. Zie de [gedeelde releasestrategie](https://github.com/woozer/ci/blob/main/docs/releases.md).

Werk op een featurebranch en gebruik een merge request:

```sh
git switch -c feature/my-change
git add .
git commit -m "Describe the change"
git push -u origin feature/my-change
```

Build en Cucumber starten automatisch. Na een geslaagde merge publiceert main ontwikkelartifacts en deployt naar dev. Start na geslaagde dev-validatie **start-release** voor de volgende patchversie, aanvankelijk `0.1.0`. Open de job om een minor-/majorversie op te geven. De release wordt gebouwd, getest, gepubliceerd en in dev gevalideerd. **publish-release** legt het eindresultaat vast. Argo CD moet voor toekomstige productie dezelfde onveranderlijke image-digest hergebruiken.

In de lokale demo neemt één account de merge- en releasebeslissing. In de echte organisatie beoordeelt een tweede persoon wijzigingen vóór ze een protected branch bereiken. De releasepipeline pusht nooit commits naar die branches.

De zelfstandige commando's in dit document werken zonder GitLab. Maven-packages worden nu naar GitLab gepubliceerd; images en charts naar lokale Artifactory. Publieke Maven-dependencies komen uit Maven Central. De HTTP-opties voor de registry gelden alleen voor deze lokale omgeving; gebruik HTTPS binnen de organisatie.

## Met Helm naar Docker Desktop Kubernetes deployen

Schakel Kubernetes in Docker Desktop in. Voor deze lokale omgeving volstaat een `kind`-cluster met één node. Bouw eerst de Jib-image en voer de commando's uit vanuit `ci/java`. Helm 4.2.4 staat lokaal in `../.tools/helm`; een apart geïnstalleerde `helm` werkt ook.

```sh
# kind nodes have their own image runtime; import the locally built Jib image.
docker image save hello-world:local | \
  docker exec -i desktop-control-plane ctr -n k8s.io images import -

../.tools/helm upgrade --install hello-world ./helm/hello-world \
  --kube-context docker-desktop \
  --namespace hello-world --create-namespace \
  --values ./helm/hello-world/values-docker-desktop.yaml \
  --rollback-on-failure --wait=watcher --timeout 5m

kubectl --context docker-desktop -n hello-world get pods,services
```

De lokale values kiezen de Jib-image `hello-world:local` en maken poort 8080 bereikbaar via Docker Desktops load balancer. De import richt zich op de enige kind-node van deze machine. Importeer de image bij extra nodes op iedere node waarop pods kunnen draaien. Stop de zelfstandige Compose-applicatie vóór de Helm-installatie: beide gebruiken localhost:8080. Test de deployment met dezelfde Cucumber-suite:

```sh
./mvnw verify -Dcucumber.base-url=http://localhost:8080
```

De chart bevat startup-, readiness- en liveness-probes, resourcelimieten en een container zonder rootrechten of extra capabilities. Het rootbestandssysteem is alleen-lezen; een tijdelijk volume is schrijfbaar. Geef voor een registry-deployment `image.repository`, `image.digest`, `image.pullPolicy=IfNotPresent` en een bestaand `imagePullSecrets`-item mee. Een digest gaat vóór `image.tag`.

```sh
# Remove only this application's Helm release.
../.tools/helm uninstall hello-world --kube-context docker-desktop --namespace hello-world
```

Bronnen: [Spring Boot-vereisten](https://docs.spring.io/spring-boot/system-requirements.html), [Cucumber JVM](https://cucumber.io/docs/installation/java/) en [Jib Maven-plugin](https://github.com/GoogleContainerTools/jib/tree/master/jib-maven-plugin).

## Aparte Angular-deployable

Start de backend met `./mvnw -pl hello-app spring-boot:run`. Voer in een tweede terminal `cd ui && npm ci && npm start` uit en open http://localhost:4200. De Angular-ontwikkelproxy stuurt API-verzoeken door naar poort 8080.

Voor Nginx gebruik je `npm run build --prefix ui` en `docker build -t hello-world-ui:local ui`. Nadat je ook `hello-world:local` met Jib hebt gebouwd, start `docker compose up -d` beide diensten. De UI staat op poort 8090. Stop eerst een clusterservice of port-forward op dezelfde poorten, of kies andere hostpoorten.

Test de UI via Cucumber in headless Chromium met `./mvnw verify -Pui -Dcucumber.base-url=http://localhost:8090`. Het browserprofiel installeert Chromium als dat ontbreekt. Linux heeft daarnaast [Playwrights systeemdependencies](https://playwright.dev/java/docs/browsers#install-system-dependencies) nodig. De standaard `./mvnw verify` vereist alleen Java en Maven. Angular-unittests draaien met `npm run test:ci --prefix ui`.

De aparte chart `helm/hello-world-ui` gebruikt dezelfde selectie onder `environment/cluster` en `environment/user` als de backend. De eigen chartdefaults leveren poort 8090 en `backend.url: http://hello-world:8080`. Wijzig `backend.url` in Helm-values als de backendservice een andere naam krijgt. Beide images/charts delen een pipelineversie, maar worden afzonderlijk gedeployed.
