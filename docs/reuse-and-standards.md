# Toekomstige optie: standaardcomponenten hergebruiken

We gebruiken voorlopig eigen componenten: actieve modules in `templates/` en ongebruikte modules in `modules/todo/`, elk als afzonderlijk YAML-bestand. Dit document beschrijft bestaande implementaties die we later kunnen overnemen. Een vervanging moet de openbare afspraken over inputs, outputs, hooks, images en foutafhandeling behouden, of de wijziging expliciet onder een nieuwe versie uitbrengen. Vóór productiegebruik blijven echte integratietests nodig.

## Werkafspraak bij wijzigingen

Geef ondersteunde GitLab-functies de voorkeur boven eigen aansturing. Controleer bij voorstellen en wijzigingen de relevante standaard of gangbare werkwijze en bestaande ondersteunde implementaties. Maak onderscheid tussen formele standaarden, platformfuncties, gangbare werkwijzen, organisatiebeleid en maatwerk.

Als we afwijken, beschrijf dan de gebruikelijke aanpak, onze reden en de gevolgen voor afnemers, onderhoud, compatibiliteit of aantoonbaarheid. Onderbouw dit waar nodig met primaire documentatie. Benoem onzekerheid en presenteer een eigen keuze niet als universele standaard. Leg belangrijke geaccepteerde afwijkingen vast bij de betreffende functie. Houd de beoordeling in verhouding tot de wijziging en binnen de bestaande toestemming van de gebruiker.

## Bewuste keuzes in de demo

| Keuze | Standaardmechanisme of gebruikelijk alternatief | Reden en gevolg |
|---|---|---|
| Automatische verplichte tests met een optionele extra Cucumber-run | GitLab-jobinputs en gewone verplichte CI-tests | Ontwikkelaars kiezen scenario's zonder de verplichte test te beperken. Een optionele fout laat de hele pipeline niet falen. |
| Tien seconden om deploymentinstellingen te wijzigen | Uitgestelde GitLab-jobs; eenvoudiger alternatieven zijn handmatige deployment of keuzes vóór de pipeline | Behoudt de gewenste keuze na een automatische start. Vereist **Unschedule** en daarna expliciet starten; er is geen popup. |
| Eén openbare ingang met aparte interne build-, deployment- en releaseconfiguratie | GitLab `include:local`, getypeerde inputs, `extends`, dynamische childpipelines en resourcegroepen | Afnemers houden één include. CI en release delen de buildjobs; deployment ontvangt alleen relevante inputs. De parent houdt de lock vast tijdens Helm én Cucumber. |
| Eigen taakcomponenten | Ondersteunde CLI's/plugins en de onderhouden componenten hieronder | Behoudt de afgesproken inputs, outputs en hooks; onderhoud en integratietests blijven onze verantwoordelijkheid. |
| Publicatie van actieve componenten in de catalogus | GitLab CI/CD Catalog en `release:` na een geteste SemVer-tag | Afnemers vinden componenten, versies en inputs op hun eigen instance. De demo-installer registreert het project; de tagpipeline publiceert de versie. |
| Unieke outputprefixes en conflictcontroles | GitLab dotenv-artifacts en expliciete `needs`; GitLab biedt geen onveranderlijke eigen outputvariabelen | Onze tests controleren de composities. Modules weigeren conflicten in ontvangen en te publiceren outputs. Dit voorkomt onbedoelde botsingen binnen die controles, maar vormt geen beveiligingsgrens tegenover vertrouwde scripts. |
| Handmatig releasemoment | Handmatige GitLab-jobs; automatisch releasen na een merge naar de default branch is ook ondersteund | We kiezen wanneer een geslaagde main-commit een officiële versie wordt. Review gebeurt vóór de merge; de knop dwingt geen tweede goedkeuring af. |
| Automatisch volgende patchnummer | SemVer bepaalt de betekenis van versies, maar verplicht geen automatische patchverhoging | Een gebruiksafspraak van de organisatie. Het team wijzigt `release-line` (major.minor) via een merge request; de releasejob verhoogt alleen de patch binnen die reeks. |

De GitLab-functies staan beschreven bij [jobinputs](https://docs.gitlab.com/ci/jobs/job_inputs/), [downstream-pipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/) en [resourcegroepen](https://docs.gitlab.com/ci/resource_groups/). GitLab regelt planning, afhankelijkheden en locks. Onze organisatie kiest de wachttijd, het handmatige releasemoment en het patchbeleid. Dat zijn geen formele industriestandaarden. Zowel [releasen na een merge naar de default branch](https://docs.gitlab.com/user/project/releases/release_cicd_examples/#create-a-release-when-a-commit-is-merged-to-the-default-branch) als een handmatige releasejob is ondersteund.

Pipelinenamen gebruiken [`workflow:name`](https://docs.gitlab.com/ci/yaml/#workflowname). Releasetoelichting en `assets.links` worden aangemaakt via de officiële [Releases API](https://docs.gitlab.com/api/releases/#create-a-release). Daarmee kan de component de gecontroleerde artifactoutputs in één verzoek vastleggen. GitLabs sleutel `release:` is ook een ondersteund alternatief. Publieke Artifactory-manifest-URL's zijn opslagafhankelijke instellingen en staan centraal. Zie [release-artifactlinks](releases.md#release-artifactlinks).

## Samenstelling van de Java-pipeline

Afnemers nemen de cataloguscomponent `ci-pipelines/java-service` op. De bestanden onder `internal/` in dat afzonderlijke project verdelen het onderhoud over build/publicatie, deployment/integratietests en release. Die indeling is onze beheerkeuze. Ze gebruikt [GitLab-includes en beperkte overerving](https://docs.gitlab.com/ci/yaml/yaml_optimization/); er is geen `flow`-schakelaar meer en de pipeline neemt zichzelf niet opnieuw op.

Het aantal YAML-bestanden neemt toe. Elke interne configuratie houdt een expliciet, getypeerd inputcontract; daardoor verdwijnen niet alle herhaalde inputdefinities. De winst zit in afgebakende verantwoordelijkheden en minder voorwaarden. We gebruiken hier geen gedeelde `spec:include`-definities: de benodigde resolutie vanuit opgenomen bestanden in een ander project is in GitLab 19.4 geïntroduceerd achter een feature flag; de demo draait op 19.3. Zie [GitLabs uitleg over externe inputbestanden](https://docs.gitlab.com/ci/inputs/#use-external-input-files-in-configuration-from-another-project).

`deployment-select` en `release-reserve` blijven een klein YAML-artifact voor hun childpipeline opleveren. GitLab ondersteunt dynamische childpipelines; de placeholdervervanging en de doorgifte van onze applicatie-instellingen zijn de eigen invulling. De deployment-child krijgt geen Maven-module, release-reeks, buildrunner of keuzelijsten meer. Release en gewone CI gebruiken dezelfde build- en publicatiejobs; release gebruikt daarnaast dezelfde Helm- en integratietestjobs als de deployment-child.

## Uitvoerbare voorbeelden voor afnemers

We volgen [GitLabs advies om componenten in CI te testen](https://docs.gitlab.com/ci/components/#test-the-component), ook met [sample-applicatiebestanden](https://docs.gitlab.com/ci/components/#test-a-component-against-sample-files). De voorbeelden zijn gecommitteerde YAML-bestanden die ongewijzigd in echte jobs worden uitgevoerd. We testen de gewijzigde bibliotheek-SHA en geven echte artifacts en outputs door. Met `strategy: mirror` laat een mislukte childpipeline ook de componentpipeline falen. Python-contracttests blijven nuttig voor foutafhandeling en hooks, als aanvulling op deze integratietests.

De vier samples en het aparte lokale project `ci-samples` zijn onze keuzes, geen GitLab-vereiste. GitLab-inputs kiezen één sample of alle samples; childpipelines en pipelines tussen projecten regelen de uitvoering. Deploymentvalidatie heeft een eigen namespace, credentials, beperkte schrijfrechten in de registry en opruimjobs. Een resourcegroep op de trigger beschermt de hele testreeks. De normale applicatiepipeline blijft zelfstandig. Zie [samples uitvoeren](../examples/samples/README.md).

Losse modules blijven de primaire manier om eigen pipelines samen te stellen. De Java-strategie is een optionele standaardsamenstelling van diezelfde modules. `helm-deploy` vraagt expliciet de naam van de aangeleverde imagevariabele. Daarmee vervalt de verborgen aanname dat de optionele verificatiemodule is gebruikt. Dit wijzigt de moduleafspraken: afnemers migreren bij een upgrade. De bestaande Java-strategie geeft deze input al mee.

## Bestaande implementaties

| Mogelijkheid | Implementatie om te beoordelen | Wat de organisatie zelf blijft bepalen |
|---|---|---|
| Maven bouwen/testen | [to be continuous Maven-component](https://to-be-continuous.gitlab.io/doc/ref/maven/) en standaard Maven-plugins | JDK-/toolversies, parent-POM, testprofielen en repositories |
| npm bouwen/testen | [to be continuous Node.js-component](https://to-be-continuous.gitlab.io/doc/ref/node/) | Lockfiles, build-/testscripts en ondersteunde Node-versie |
| Helm-deployment | [to be continuous Helm-component](https://to-be-continuous.gitlab.io/doc/ref/helm/) | Chart, image-digestkoppeling, omgevingen, RBAC en goedkeuringen |
| Sonar-analyse en gate | SonarScanner met `sonar.qualitygate.wait=true`; ook de [to be continuous Sonar-component](https://to-be-continuous.gitlab.io/doc/ref/sonar/) is een optie | Kwaliteitsprofiel, gatebeleid, coveragepaden en servercredentials |
| Fortify | [OpenText Fortify AST Scan-component](https://gitlab.com/Fortify/components/ast-scan) of [Fortify fcli-component](https://fortify.github.io/fcli/v3/ci/gitlab/v2.0.x/fcli-component.html) voor eigen reeksen | SSC/ScanCentral of FoD, licenties, beveiligingsbeleid en vertaling van resultaten |
| Dependency-, container- en geheimenscans | [GitLab-beveiligingstemplates/-componenten](https://docs.gitlab.com/user/application_security/detect/security_configuration/) waar de editie die ondersteunt | Ernstgrenzen, uitzonderingen, actualiteit van feeds en verplichte merge-/releasecontroles |
| OWASP Dependency-Check | [Officiële Maven-plugin](https://dependency-check.github.io/DependencyCheck/dependency-check-maven/check-mojo.html) | Pluginversie, NVD-feedtoegang, CVSS-grens en beoordeelde uitzonderingen |
| Images ondertekenen | [Sigstore Cosign](https://docs.sigstore.dev/cosign/key_management/overview/) | KMS/OIDC-vertrouwen, ondertekenrechten en verificatie-/admissionbeleid |
| OWASP-runtimechecks | [ZAP-scans in Docker](https://www.zaproxy.org/docs/docker/baseline-scan/) | Doel en authenticatie, scanbereik, actieve/passieve tests en beleid |
| Cucumber-integratietests | [Cucumber-ondersteuning in Maven Failsafe](https://maven.apache.org/components/surefire/maven-failsafe-plugin/examples/cucumber.html) | Scenario's, runner, doel-URL, testdata en assertions |

Dit zijn onderhouden implementaties, maar niet allemaal officiële GitLab-producten. **to be continuous is een verzameling componenten van een derde partij.** Beoordeel onderhoud, licentie, compatibiliteit en ondersteuning. Een vermelding in een catalogus is geen beveiligingscertificaat. Gepubliceerde voorbeelden kunnen meeschuivende versies of images bevatten; selecteer en test vaste versies vóór invoering.

## Welke mogelijkheden bestaan al?

- Componenten accepteren configureerbare inputs en kiezen jobimages.
- GitLabs `needs` met artifacts/dotenv regelt de jobvolgorde en overdracht van resultaten. Een extra pipeline-engine is niet nodig.
- De architectuur van to be continuous gebruikt dotenv-outputs tussen templates. Deploymenttemplates leveren omgevingsinformatie voor acceptatietests. Ondersteuning voor hooks en commando-uitbreidingen verschilt per template; controleer de foutafhandeling van de gekozen versie. Zie [de architectuur](https://to-be-continuous.gitlab.io/doc/dev/architecture/).
- SonarScanner kan op de quality gate wachten. Analyse en de bijbehorende gate vormen één taak voor de afnemer; combineren vermijdt eigen pollingcode. Zie [Sonar-parameters](https://docs.sonarsource.com/sonarqube-server/2026.1/analyzing-source-code/analysis-parameters/parameters-not-settable-in-ui).
- Fortify levert een complete AST-workflow en een fcli-component voor meer controle. Hergebruik de inrichting en scanafhandeling. Pas die aan waar organisatiebeleid of editiegebonden integratie dat vraagt.

De eigen component `handoff` en het callbackprotocol `next(work)` zijn verwijderd. Extra bewerkingen zijn gewone GitLab-jobs met een eigen image en `needs`. GitLab plant de volgende verplichte job na succes; artifacts en dotenv geven resultaten door. Afnemers van een oudere vaste bibliotheekversie moeten deze component vervangen voordat ze upgraden. Zie [uitbreidingspatronen](modules.md#eigen-gedrag-toevoegen).

Eén logische component hoeft niet precies één fysieke job te betekenen. Leverancierscomponenten kunnen aparte jobs voor voorbereiding, scans en rapportage nodig hebben. Houd waar mogelijk één verantwoordelijkheid per bouwblok, zonder een geteste leveranciersworkflow alleen voor een vaste jobtelling op te splitsen.

## Aansluiting op standaarden aantonen

| Referentie | Benodigd bewijs | Status van het prototype |
|---|---|---|
| [NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final) | Beheerde toolchains, beschermde broncode/artifacts, vastgelegde tests en opvolging van kwetsbaarheden | Een deel van de pipelinepatronen is beschreven; organisatiebrede werkwijzen en handhaving zijn niet ingericht |
| [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) | Geselecteerde beveiligingseisen voor de applicatie met verificatiebewijs | Scanners dekken een deel; dreigingsmodellering, applicatiecontroles en handmatige verificatie blijven nodig |
| [SLSA-buildeisen](https://slsa.dev/spec/v1.2/build-requirements) | Herkomstbewijs gekoppeld aan artifact-digests, een passende vertrouwde/geïsoleerde buildomgeving en verificatie | Deployment op digest is getest; signing, herkomstbewijs en beoordeling van de buildomgeving staan nog open |

Imagehandtekeningen en een SBOM tonen op zichzelf geen SLSA-niveau aan. Geslaagde scans bewijzen evenmin ASVS-conformiteit. Een grens van 80% testdekking is organisatiebeleid, geen universele standaard.

Verplichte beveiligingscontroles moeten blijven gelden als applicatie-YAML en hooks veranderen. GitLab Ultimate biedt [pipeline execution policies](https://docs.gitlab.com/user/application_security/policies/pipeline_execution_policies/) voor centrale handhaving. Ontwerp voor andere edities overeenkomstige beschermde release-/beleidscontroles met de beschikbare functies. Scans rapporteren bevindingen; configureer daarnaast expliciet wanneer die een merge of release blokkeren.

## Later een standaardcomponent overnemen

1. Kies één kandidaat voor een concrete behoefte. De tabel is een beoordelingslijst, geen besluit om over te stappen.
2. Vergelijk de afspraken met onze component: inputs, outputs, artifactpaden, images/tools, hooklifecycle, jobafhankelijkheden en foutafhandeling.
3. Zet versie en images vast, beoordeel licentie en runnervereisten en gebruik ondersteunde uitbreidingspunten of een kleine adapter voor verenigbare verschillen.
4. Test de vervanging met contracttests en representatieve applicaties. Controleer ook scanfouten, ontbrekende rapporten, mislukte hooks en geblokkeerde productiepromotie. Geef onverenigbare wijzigingen een nieuwe versie en migreer afnemers expliciet.
5. Voer één vervanging tegelijk in. Behoud beleidshandhaving en bewijseisen en beoordeel aansluiting op standaarden los van de leverancier van de component.

In de lokale omgeving zijn GitLab-pipelines, Maven-publicatie, Jib-/Helm-publicatie naar Artifactory, Kubernetes-deployment, Cucumber en releasebescherming uitgevoerd. Scanner-, Fortify- en KMS/signing-integraties moeten nog echt worden gevalideerd. Standaardcomponenten blijven een toekomstige optie.

Het [onderzoek naar gelijktijdige deployments](deployment-concurrency.md) vergelijkt gewone jobs met de huidige childpipeline. GitLab ondersteunt `oldest_first` voor pipelinevolgorde. De lokale experimenten laten ook zien waarom het herhalen van oude jobs extra aandacht vraagt. Het onderzoek beschrijft mogelijkheden en bewijs zonder het huidige deliverybeleid te wijzigen.

## Angular-UI en browsertests

De optionele input `ui-directory` activeert de bestaande npm-, image- en Helm-modules in dezelfde centrale pipeline. GitLabs `rules`, `needs` en artifacts verbinden de jobs. Backend en UI hebben aparte images, Helm-releases en deployments; één repositoryrelease geeft beide dezelfde versie. Dit is onze samenstelling, geen nieuwe pipeline-engine of formele standaard. Meer deployables kunnen losse modules gebruiken; deze demosamenstelling ondersteunt één backend en één UI.

De UI gebruikt een Angular CLI-workspace, een lockfile en `npm ci`. De [onderhouden Nginx-image zonder rootrechten](https://github.com/nginx/docker-nginx-unprivileged) serveert statische bestanden en stuurt `/api/` door naar de backend. Het ondersteunde mechanisme voor omgevingstemplates stelt de backend-URL in. Beide deployments gebruiken de gekozen cluster-/gebruikerswaarden. Chartspecifieke instellingen, zoals de servicepoort, staan in de chartdefaults.

Dockerfile-images gebruiken [GitLabs beschreven aanpak met rootless BuildKit](https://docs.gitlab.com/ci/docker/using_buildkit/). In deze Docker Desktop-omgeving gebruikt de aparte runner `local-buildkit` Dockers standaard-seccomp-profiel, aangevuld met `clone`, `unshare`, `setns`, `mount` en `umount2`. De runner is niet privileged en mount de Docker-socket niet in jobs. Dit is lokale runnerconfiguratie die voor een andere host opnieuw moet worden beoordeeld. De tool-image bevat Python voor registry-authenticatie en metadata. De Java-image wordt met Jib gebouwd.

Cucumber-UI-scenario's gebruiken de officiële [Playwright Java API](https://playwright.dev/java/docs/test-runners) met headless Chromium. Ook headless uitvoering vereist een browserengine. De Cucumber-component kiest een [Playwright-browserimage](https://playwright.dev/java/docs/docker), uitgebreid met onze Java 25- en Maven-versies. Gewone backendtests gebruiken de kleinere Java-image. Browser- en Java-dependencyversies moeten overeenkomen. De CI-browser test onze eigen applicatie met de standaardinstellingen van de image; deze inrichting is niet bedoeld om willekeurige onbetrouwbare websites te bezoeken.

Scenario's met `@ui` draaien na beide deployments en zijn verplicht voor afronding van een release. Ze vergelijken de getoonde tabel met het werkelijke API-antwoord in de browser, vernieuwen de lijst en testen een mobiele schermgrootte. Screenshots staan in het Cucumber-rapport; bij fouten worden ook Playwright-traces bewaard. Een eigen Cucumber/Playwright-adapterdienst is niet nodig.

## Een kleine componentcatalogus houden

`maven-build` volgt de gewone Maven-lifecycle: `package` omvat Surefire-unittests. Cucumber/Failsafe blijft een afzonderlijke integratieteststap. De voorbereide `maven-test`-module is hiermee samengevoegd. JUnit-rapporten horen bij de build; JaCoCo-configuratie hoort in de POM. Publicatie slaat de al uitgevoerde unit- en integratietests over en moet via `needs` van de geslaagde validatie afhangen. Zie [Mavens build-lifecycle](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html).

Ontwerp één component per herkenbare taak voor de afnemer. GitLab staat meerdere jobs binnen één component toe. Een losse technische stap vereist daarom geen eigen publieke module. Splits alleen op bij aantoonbaar zelfstandig gebruik, verschillende rechten of verschillende uitvoeringsmomenten. Dit is onze ontwerpafspraak binnen [GitLabs componentmodel](https://docs.gitlab.com/ci/components/).

De TODO-modules zijn op drie plaatsen samengevoegd: `sonar` verzorgt analyse en de native quality gate, `fortify` combineert scan en beleidscontrole, en `image-scan` maakt ook het CycloneDX-SBOM. Daarmee vervallen drie losse componenten en de eigen Sonar-pollingcode. Dit is een keuze voor eenvoud, geen voorgeschreven industriestandaard. `sonar` is met Dependency-Check opgenomen in de actieve verzameling. `fortify` en `image-scan` blijven in `modules/todo/` voor latere integratie. Zie de [scanhandleiding](scanners.md) voor de gratis demo-inrichting.

Gebruik bij migratie `sonar.yml` in plaats van `sonar-scan.yml` en `sonar-gate.yml`, en `fortify.yml` in plaats van de twee Fortify-bestanden. Laat vervolgjobs via `needs` op `sonar` respectievelijk `fortify` wachten. Sonar publiceert `SONAR_TASK_FILE`; het algemene `SONAR_STATUS=passed` omvat de gate. Fortify publiceert `FORTIFY_RECEIPT` en `FORTIFY_REPORT`; geef beide adapterpaden aan die ene component mee. Haal het SBOM voortaan via `IMAGE_SCAN_SBOM` en artifacts van `image-scan` op. De losse `sbom.yml` vervalt. Het uitgebreide profiel gebruikt voortaan één `fortify-image` en `fortify-job-timeout`; aparte gate- en SBOM-images vervallen.

Ondertekenen en verifiëren kunnen afzonderlijk nuttig blijven vanwege verschillende rechten en zelfstandig gebruik bij deployment. Release reserveren en publiceren hebben verschillende uitvoeringsmomenten. Een interne releasecontrole hoeft daarentegen niet vanzelf een afzonderlijke publieke module te zijn. Beoordeel de winst voor afnemers vóór uitbreiding van de catalogus.

## Drie broncoderepositories

`ci-components`, `ci-pipelines`, `hello-world` en `ci-samples` hebben elk een eigen openbare GitHub-repository. De componentbibliotheek koppelt de pipeline- en applicatierepositories via [Git-submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules). Dit is een ingebouwde Git-functie: de bovenliggende repository bewaart een verwijzing naar een vaste commit. De keuze om daarmee de demo samen te stellen is onze beheerafspraak.

Voor de volledige demo gebruiken we `git clone --recurse-submodules`. Alleen afnemers van de CI-bibliotheek hebben de applicatiecheckouts niet nodig. Wijzig applicatiebroncode in de betreffende repository en publiceer die commit eerst; werk daarna de submoduleverwijzing in `ci-components` bij via een beoordeelde wijziging. Een gewone update van de componentbibliotheek wordt gevolgd door `git submodule update --init --recursive`.

De installer vult alleen lege GitLab-projecten met de vastgelegde lokale broncode en geschiedenis. Een wijziging op GitHub wordt dus niet automatisch naar een bestaande GitLab-repository gesynchroniseerd. De moduleversie `1.0.0` en de submodulecommits hebben verschillende doelen: de versie kiest de CI-componenten; de commits leggen de applicatiebroncode voor een nieuwe demo vast.

## Afzonderlijke pipelinebibliotheek

De losse taken blijven samen in **ci-components**; de standaardpipeline staat in **ci-pipelines**. GitLab ondersteunt componenten die andere componenten opnemen en adviseert vaste releases voor externe afhankelijkheden. Onze pipeline gebruikt daarom overal dezelfde geteste componentversie. De gescheiden releasecycli en het gebruik van een Git-submodule voor de lokale installer zijn onze beheerkeuzes. De installer is geen runtimeafhankelijkheid van een module of pipeline. Zie [GitLabs afhankelijkhedenadvies](https://docs.gitlab.com/ci/components/#manage-dependencies).

De complete pipeline beheert bewust globale `workflow`, `stages` en defaults. GitLab raadt globale instellingen af voor vrij combineerbare taakcomponenten; onze samengestelde pipeline wordt eenmaal opgenomen en beheert de gehele applicatiepipeline. Afnemers die zelf willen combineren, kiezen de losse modules.
