# Gebruik in de eigen organisatie

Dezelfde modules kunnen met eigen GitLab-runners, Artifactory, SonarQube en OpenShift werken. Het platformteam beheert de gedeelde instellingen; een applicatieteam kiest de omgeving en het Helm-profiel. De lokale installer bouwt een demo op. Gebruik die niet om bestaande organisatiediensten opnieuw te installeren of hun accounts te vervangen.

## Configuratie op drie plekken

| Plek | Inhoud | Beheerder |
|---|---|---|
| Gedeelde organisatie-YAML | Serveradressen, goedgekeurde images, runner-tags en publicatie-instellingen | Platformteam |
| GitLab CI/CD-variabelen of de bestaande secretmanager | Registry-credentials, scantokens en eventueel een kubeconfig | Platformteam, met rechten per project en omgeving |
| `environment/cluster/` en `environment/user/` in de applicatie | Helm-values voor het cluster en het gekozen applicatieprofiel | Applicatieteam |

Gebruik hiervoor gewone GitLab-includes, inputs en variabelen. Een eigen configuratieloader is niet nodig. De bestandsindeling is onze afspraak; de onderliggende mechanismen zijn ondersteunde GitLab- en Helm-functionaliteit.

Gedeelde variabelen kunnen op groepsniveau staan. Beperk gevoelige deploymentvariabelen tot de jobs van de bijbehorende omgeving en gebruik protected variabelen waar alleen beschermde branches toegang mogen hebben. Masking vervangt geen review of toegangsbeheer. Omgevingsscopes voor **groepsvariabelen** vereisen Premium of Ultimate; in de lokale CE-demo kunnen we scopes op **projectvariabelen** gebruiken. Zie [GitLab-variabelen](https://docs.gitlab.com/ci/variables/) en [omgevingsscopes](https://docs.gitlab.com/ci/environments/#limit-the-environment-scope-of-a-cicd-variable).

Gebruik omgevingsgebonden secrets tijdens de job, niet om `include` of `rules` te evalueren. De omgeving en toegestane keuzes moeten bij het samenstellen van de pipeline bekend zijn. Een Helm-values-bestand bevat geen credentials en kiest op zichzelf geen Kubernetes-context.

## Bestaande organisatie-images gebruiken

De organisatie heeft al Java- en Nginx-images. Gebruik die als uitgangspunt en leg de goedgekeurde referenties centraal vast. De applicatie hoeft deze referenties niet per job te herhalen.

| Taak | Bestaande configuratie | Vereisten |
|---|---|---|
| Java bouwen en backendtests uitvoeren | `JAVA_CI_IMAGE`, gekoppeld aan onder meer `MAVEN_BUILD_IMAGE` en `CUCUMBER_TEST_IMAGE` | Bijpassende JDK, shell en Maven of de benodigdheden voor Maven Wrapper |
| Java-applicatie met Jib verpakken | `JAVA_RUNTIME_IMAGE`, gekoppeld aan `JIB_BASE_IMAGE` | Goedgekeurde Java-runtime voor de doelarchitectuur en het cluster |
| Angular bouwen en testen | `NODE_CI_IMAGE`, gekoppeld aan `NPM_BUILD_IMAGE` en `NPM_TEST_IMAGE` | Node.js en npm passend bij de applicatie |
| Angular-bestanden serveren | `NGINX_RUNTIME_IMAGE`, gekoppeld aan `NGINX_BASE_IMAGE` | De bestaande organisatie-Nginx-image als basis voor de applicatie-image |

De Java-buildimage en runtime mogen verschillende images zijn. Een image met alleen een Java-runtime is niet voldoende om Java te compileren. Nginx serveert de bestanden die de npm-build heeft opgeleverd; de Angular-build zelf gebruikt Node.

Controleer bij de organisatie-Nginx-image de documentroot, luisterpoort, schrijfbare directories en het mechanisme voor de backend-URL. De huidige UI-Dockerfile gebruikt de entrypointscripts van `nginx-unprivileged` om `BACKEND_URL` in een configuratietemplate te verwerken. Een andere Nginx-image ondersteunt dat niet automatisch. Pas de applicatie-Dockerfile en chart aan de afspraken van de organisatie-image aan; de npm- en image-buildmodules kunnen dezelfde taken blijven uitvoeren.

Gebruik lokaal de demo-images zolang de interne registry niet bereikbaar is. De interne imagereferenties en registry-toegang worden pas in de echte omgeving ingesteld. Voor een overstap tussen Intel en ARM moeten zowel de toolimages als de runtime-images de doelarchitectuur ondersteunen.

## OpenShift verbinden

De bestaande component `helm-deploy` ondersteunt twee vormen van clustertoegang:

- Een GitLab Kubernetes-agent: GitLab levert `KUBECONFIG`; `KUBE_CONTEXT` selecteert de toegestane verbinding. Er hoeft dan geen persoonlijk kubeconfig-bestand op de laptop te staan.
- Een kubeconfig als GitLab-bestandsvariabele: `kubeconfig-variable` bevat de naam van die variabele. Het platform beheert het serviceaccount, de beperkte rechten en de rotatie.

Gebruik bij voorkeur de clustertoegang die het platformteam al beheert. De agent is een ondersteunde GitLab-integratie, geen verplichting of aparte OpenShift-deploymentmodule. Autoriseer alleen de benodigde projecten en beperk de clusterrechten. Zie [GitLab CI/CD met de Kubernetes-agent](https://docs.gitlab.com/user/clusters/agent/ci_cd_workflow/).

De clusterkeuze moet zowel de verbinding als de bijpassende Helm-values en test-URL selecteren. `user_config` wijzigt alleen applicatie-instellingen, zoals replica's en resources. Het platform maakt de OpenShift-projecten/namespaces aan; de deployment gebruikt `create-namespace: false`. De afnemer hoeft geen login- of deploymentscript toe te voegen.

OpenShift vereist ook passende charts en images. Controleer de toegestane willekeurige gebruikers-ID, schrijfbare directories, SCC's, registry-pullrechten en de gekozen Route of Ingress met TLS. De huidige demo gebruikt LoadBalancer-services en heeft nog geen Route-template. Alleen een andere kubeconfig invullen bewijst daarom niet dat de volledige applicatie op OpenShift werkt. Zie [Red Hats richtlijnen voor images](https://docs.redhat.com/en/documentation/openshift_container_platform/4.19/html/images/creating-images).

## Wat al kan en wat nog moet worden aangepast

Losse modules hebben al inputs voor eigen images, registry-adressen en deploymentinstellingen. Groeps- en projectvariabelen kunnen de serveradressen en imagekoppelingen uit `config/organization.yml` overschrijven.

De standaardpipeline houdt lokale defaults voor de demo, maar accepteert nu expliciete platforminstellingen:

| Instelling | Doel |
|---|---|
| `runner-tags`, `buildkit-runner-tags` | De runners van de organisatie selecteren |
| `registry-plain-http: false` | HTTPS gebruiken bij Jib-, BuildKit- en Helm-publicatie/deployment |
| `kubeconfig-variable` | Een eigen GitLab-bestandsvariabele kiezen; leeg laat de Kubernetes-agent `KUBECONFIG` leveren |
| `clusters`, `cluster` | De toegestane clusterkeuzes en de beginselectie |
| `user-configs`, `user-config` | De toegestane Helm-profielen en de beginselectie |
| `namespace` | De vooraf ingerichte doelnamespace |

Deze zijn inputs van de standaardsamenstelling, geen nieuwe verplichte inputs van de losse modules. De platforminstellingen worden ook aan deployment- en release-childpipelines doorgegeven. De defaults hoeven in de demo niet te worden herhaald. Werk bij een eigen keuzelijst ook het gedeelde formulier `config/pipeline-inputs.yml` in **ci-pipelines** bij; GitLab kan de opties daar niet uit runtimevariabelen afleiden.

Deploymentjobs gebruiken `dev/<cluster>`; de dev-validatie van releaseartifacts gebruikt `release/dev/<cluster>`. Stel de context of kubeconfig en de test-URL's in voor de overeenkomende omgevingsscope. Gebruik bijvoorbeeld `dev/openshift-test` en `release/dev/openshift-test` voor dezelfde testomgeving. Hiermee kiezen verbinding, credentials en test-URL dezelfde bestemming als `environment/cluster/openshift-test.yaml`. De keuze zelf verleent geen rechten: die blijven in GitLab en cluster-RBAC geregeld.

`MAVEN_PUBLISH_URL` en `MAVEN_PUBLISH_SERVER_ID` selecteren de Maven-repository. De demo gebruikt GitLab Package Registry; de organisatie kan haar Artifactory-Maven-repository instellen en de overeenkomende credentials via `MAVEN_PUBLISH_SETTINGS` als bestandsvariabele leveren. Java-/Node-/Nginx-images en andere adressen gebruiken de gedeelde variabelen hierboven. Beheer organisatiebrede standaardwaarden centraal; een afnemer hoeft alleen afwijkende applicatiekeuzes door te geven.

Deze wijzigingen zijn bedoeld voor publicatie met de bijgewerkte bibliotheek. Oudere vastgezette versies behouden hun eerdere gedrag. Er is nog geen verbinding met of integratievalidatie op de echte OpenShift-omgeving uitgevoerd.

De releaseafspraak blijft gelijk: een release levert vaste artifactversies en image-digests op. Dev mag die deployen en testen. De latere productiedeployment via Argo CD gebruikt dezelfde digests zonder opnieuw te bouwen.
